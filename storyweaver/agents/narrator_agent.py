"""
NarratorAgent — 核心叙事生成
调用 DeepSeek 生成旁白、对话和暗线碎片。

提供两种调用方式：
  run_narrator_agent(state)   → dict          普通调用，等待完整响应
  stream_narrator_agent(state) → Generator   流式调用，逐 token 推送叙事文本
"""
import json
import re
import time
from storyweaver.config import get_client, MODEL, GENERATION_TEMPERATURE
from storyweaver.schemas import GameState
from prompts.world_setting import WORLD_SYSTEM_PROMPT
from prompts.narrator_prompts import build_narrator_prompt


def run_narrator_agent(state: GameState) -> dict:
    client = get_client()
    logs   = list(state.get("agent_logs", []))
    t0     = time.time()

    user_prompt = build_narrator_prompt(state)

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": WORLD_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=GENERATION_TEMPERATURE,
            response_format={"type": "json_object"},
            max_tokens=900,
        )
        raw     = resp.choices[0].message.content
        result  = json.loads(raw)
        latency = (time.time() - t0) * 1000

        narration = result.get("narration", "").strip()
        if not narration:
            narration = "前路风尘，一时无话。"

        # 规范化 dialogue 字段
        dialogue = result.get("dialogue") or {}
        if isinstance(dialogue, dict):
            if not dialogue.get("speaker") or not dialogue.get("text"):
                dialogue = {}

        # 规范化 state_delta
        delta = result.get("state_delta") or {}
        _normalize_delta(delta)

        logs.append(f"[NarratorAgent] generated {len(narration)} chars in {latency:.0f}ms")
        return {
            "narration":          narration,
            "dialogue":           dialogue,
            "backstory_fragment": result.get("backstory_fragment", "") or "",
            "state_delta":        delta,
            "agent_logs":         logs,
            "latency_ms":         latency,
        }

    except Exception as exc:
        latency = (time.time() - t0) * 1000
        logs.append(f"[NarratorAgent] error: {exc}")
        return {
            "narration":          "（叙事引擎暂时失语，旅途静默片刻。）",
            "dialogue":           {},
            "backstory_fragment": "",
            "state_delta":        {},
            "agent_logs":         logs,
            "latency_ms":         latency,
        }


def stream_narrator_agent(state: GameState):
    """流式叙事生成器。

    Yields:
        {"type": "chunk", "text": str}   — 叙事文本片段（实时推送）
        {"type": "done",  "result": dict} — 完整解析结果（流结束后一次性推送）

    原理：DeepSeek stream=True 返回 JSON token 流，用正则从累积 buffer 中
    增量提取 "narration" 字段值，只把新增字符 yield 出去；流结束后解析完整 JSON
    取得 dialogue / backstory_fragment / state_delta。
    """
    client      = get_client()
    logs        = list(state.get("agent_logs", []))
    t0          = time.time()
    user_prompt = build_narrator_prompt(state)

    # 匹配 JSON 中 "narration": "已流入的文本（含转义）
    _NARRATION_RE = re.compile(r'"narration"\s*:\s*"((?:[^"\\]|\\.)*)')

    def _decode_json_str(raw: str) -> str:
        """把 JSON 字符串内容的转义序列还原成可读文本。"""
        return (raw
                .replace('\\n', '\n')
                .replace('\\t', '\t')
                .replace('\\"', '"')
                .replace('\\\\', '\\'))

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": WORLD_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=GENERATION_TEMPERATURE,
            stream=True,
            max_tokens=900,
        )

        buffer       = ""
        yielded_len  = 0   # 已经 yield 出去的叙事字符数（decoded 后）

        for chunk in resp:
            delta = chunk.choices[0].delta.content or ""
            if not delta:
                continue
            buffer += delta

            # 用正则从 buffer 里提取目前累积的 narration 原始内容
            m = _NARRATION_RE.search(buffer)
            if not m:
                continue

            decoded = _decode_json_str(m.group(1))
            if len(decoded) > yielded_len:
                new_text = decoded[yielded_len:]
                yielded_len = len(decoded)
                yield {"type": "chunk", "text": new_text}

        # ── 流结束，解析完整 JSON ─────────────────────────────────────────
        latency = (time.time() - t0) * 1000
        try:
            result = json.loads(buffer)
        except json.JSONDecodeError:
            result = {}

        narration = result.get("narration", "").strip() or "前路风尘，一时无话。"

        dialogue = result.get("dialogue") or {}
        if isinstance(dialogue, dict):
            if not dialogue.get("speaker") or not dialogue.get("text"):
                dialogue = {}

        delta_obj = result.get("state_delta") or {}
        _normalize_delta(delta_obj)

        logs.append(f"[NarratorAgent] streamed {len(narration)} chars in {latency:.0f}ms")
        yield {
            "type": "done",
            "result": {
                "narration":          narration,
                "dialogue":           dialogue,
                "backstory_fragment": result.get("backstory_fragment", "") or "",
                "state_delta":        delta_obj,
                "agent_logs":         logs,
                "latency_ms":         latency,
            },
        }

    except Exception as exc:
        latency = (time.time() - t0) * 1000
        logs.append(f"[NarratorAgent] stream error: {exc}")
        yield {"type": "chunk", "text": "（叙事引擎暂时失语，旅途静默片刻。）"}
        yield {
            "type": "done",
            "result": {
                "narration":          "（叙事引擎暂时失语，旅途静默片刻。）",
                "dialogue":           {},
                "backstory_fragment": "",
                "state_delta":        {},
                "agent_logs":         logs,
                "latency_ms":         latency,
            },
        }


def _normalize_delta(delta: dict) -> None:
    """确保 state_delta 中所有字段类型正确。"""
    delta.setdefault("companion_relation_change", 0)
    delta.setdefault("reputation_change", 0)
    delta.setdefault("silver_change", 0)
    delta.setdefault("inventory_add", [])
    delta.setdefault("inventory_remove", [])
    delta.setdefault("new_location", "")
    delta.setdefault("locations_add", [])
    delta.setdefault("flags_set", {})
    delta.setdefault("npc_updates", {})

    # 类型保护
    for key in ("companion_relation_change", "reputation_change", "silver_change"):
        try:
            delta[key] = int(delta[key])
        except (TypeError, ValueError):
            delta[key] = 0

    for key in ("inventory_add", "inventory_remove", "locations_add"):
        if not isinstance(delta[key], list):
            delta[key] = []
