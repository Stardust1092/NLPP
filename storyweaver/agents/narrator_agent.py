"""
NarratorAgent — 核心叙事生成
调用 DeepSeek 生成旁白、对话和暗线碎片。
"""
import json
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
