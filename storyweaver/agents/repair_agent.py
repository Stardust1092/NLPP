"""
RepairAgent — 一致性修复
当 consistency_agent 检测到矛盾时，生成叙事化的拒绝旁白，
自然融入游戏语境，不暴露"系统错误"。
"""
import json
from storyweaver.config import get_client, MODEL
from storyweaver.schemas import GameState
from prompts.consistency_prompts import REPAIR_NARRATION_PROMPT


def run_repair_agent(state: GameState) -> dict:
    client   = get_client()
    logs     = list(state.get("agent_logs", []))
    violation       = state.get("consistency_violation", "")
    repair_hint     = state.get("repair_suggestion", "")
    player_input    = state.get("player_input", "")
    location        = state.get("player_location", "")

    logs.append(f"[RepairAgent] generating repair narration for: {violation}")

    prompt = REPAIR_NARRATION_PROMPT.format(
        player_input     = player_input,
        violation        = violation,
        repair_suggestion= repair_hint,
        location         = location,
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            response_format={"type": "json_object"},
            max_tokens=300,
        )
        result   = json.loads(resp.choices[0].message.content)
        narration = result.get("narration") or repair_hint or "此行动在当下无从施为，你需另寻他法。"
        logs.append("[RepairAgent] repair narration generated")
        return {
            "narration":          narration,
            "dialogue":           {},
            "backstory_fragment": "",
            "state_delta":        {},        # 矛盾修复回合不更改状态
            "agent_logs":         logs,
        }
    except Exception as exc:
        logs.append(f"[RepairAgent] error: {exc}, using fallback text")
        fallback = repair_hint or "此行动在当下无从施为，你需另寻他法。"
        return {
            "narration":          fallback,
            "dialogue":           {},
            "backstory_fragment": "",
            "state_delta":        {},
            "agent_logs":         logs,
        }
