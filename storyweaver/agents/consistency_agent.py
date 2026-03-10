"""
ConsistencyAgent — 一致性检测
规则检查优先，复杂情形回退到 DeepSeek 验证。
"""
import json
from storyweaver.config import get_client, MODEL, CONSISTENCY_TEMPERATURE
from storyweaver.schemas import GameState
from prompts.consistency_prompts import CONSISTENCY_CHECK_PROMPT


def run_consistency_agent(state: GameState) -> dict:
    logs         = list(state.get("agent_logs", []))
    player_input = state.get("player_input", "")
    intent       = state.get("intent", "OTHER")
    entities     = state.get("entities", {})
    inventory    = state.get("inventory", [])
    npcs_status  = state.get("npcs_status", {})
    plot_flags   = state.get("plot_flags", {})
    location     = state.get("player_location", "")

    # ── 规则 1：使用不存在道具 ──────────────────────────────────────────────
    if intent == "USE_ITEM":
        item = entities.get("item_name", "")
        if item and not any(item in inv for inv in inventory):
            logs.append(f"[ConsistencyAgent] FAIL rule1: '{item}' not in inventory")
            return _fail(f"背包中没有「{item}」，无法使用。",
                         f"你的背包里没有{item}。可以先寻找、购买，或尝试其他方法。",
                         logs)

    # ── 规则 2：穗不能开口说话 ──────────────────────────────────────────────
    for pattern in ["穗说", "穗回答", "穗开口", "穗大声"]:
        if pattern in player_input:
            logs.append(f"[ConsistencyAgent] FAIL rule2: 穗 cannot speak")
            return _fail("穗是哑女，无法开口说话。",
                         "穗无法说话，她只能以布条写字或用眼神手势表达。",
                         logs)

    # ── 规则 3：与不在场或已死亡 NPC 交互 ──────────────────────────────────
    target_npc = entities.get("target_npc", "")
    if target_npc and target_npc in npcs_status:
        npc_info = npcs_status[target_npc]
        if not npc_info.get("alive", True):
            logs.append(f"[ConsistencyAgent] FAIL rule3: NPC '{target_npc}' is dead")
            return _fail(f"「{target_npc}」已不在人世，无法与之交互。",
                         f"{target_npc}已经不在了，无法进行此行动。",
                         logs)

    # ── 规则 4：在知晓豚妖之前提及豚妖 ─────────────────────────────────────
    if "豚妖" in player_input and not plot_flags.get("knows_pig_demon", False):
        logs.append(f"[ConsistencyAgent] FAIL rule4: player doesn't know about pig demon")
        return _fail("你尚不知晓豚妖的存在，无从对此做出反应。",
                     "在了解真相之前，你无法知道委托背后隐藏的秘密。",
                     logs)

    # ── 规则 5：贿赂但铜钱不足 ─────────────────────────────────────────────
    if intent == "BRIBE" and state.get("silver", 0) <= 0:
        logs.append("[ConsistencyAgent] FAIL rule5: no silver for bribe")
        return _fail("身无分文，无从打点。",
                     "你的铜钱已经用尽，无法以钱财打点他人。",
                     logs)

    # ── LLM 深层检查（仅对较复杂输入启用）──────────────────────────────────
    if len(player_input) > 8:
        result = _llm_check(state, logs)
        if not result.get("consistency_passed", True):
            return result

    logs.append("[ConsistencyAgent] PASS")
    return {
        "consistency_passed":    True,
        "consistency_violation": "",
        "repair_suggestion":     "",
        "agent_logs":            logs,
    }


def _fail(violation: str, repair: str, logs: list) -> dict:
    return {
        "consistency_passed":    False,
        "consistency_violation": violation,
        "repair_suggestion":     repair,
        "agent_logs":            logs,
    }


def _llm_check(state: GameState, logs: list) -> dict:
    """DeepSeek 深层一致性检查。"""
    client       = get_client()
    recent_turns = state.get("turn_history", [])[-3:]
    recent_text  = "\n".join(
        f"  - 第{t.get('turn_id','?')}轮：{t.get('player_input','')} → {t.get('narration','')[:40]}…"
        for t in recent_turns
    ) or "  （旅途起点）"

    npcs_present = [
        name for name, info in state.get("npcs_status", {}).items()
        if info.get("alive", True) and state.get("player_location", "") in info.get("location", "")
    ]

    prompt = CONSISTENCY_CHECK_PROMPT.format(
        location       = state.get("player_location", ""),
        inventory      = ", ".join(state.get("inventory", [])) or "空",
        plot_flags     = json.dumps({k: v for k, v in state.get("plot_flags", {}).items() if v},
                                    ensure_ascii=False),
        trust_level    = "较高" if state.get("companion_relation", 0) > 50 else "较低",
        present_npcs   = ", ".join(npcs_present) or "无",
        recent_history = recent_text,
        player_input   = state.get("player_input", ""),
        intent         = state.get("intent", "OTHER"),
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=CONSISTENCY_TEMPERATURE,
            response_format={"type": "json_object"},
            max_tokens=250,
        )
        result = json.loads(resp.choices[0].message.content)
        violation = result.get("violation", "").strip()
        if not result.get("passed", True) and violation:
            logs.append(f"[ConsistencyAgent] LLM FAIL: {violation}")
            return {
                "consistency_passed":    False,
                "consistency_violation": violation,
                "repair_suggestion":     result.get("repair", ""),
                "agent_logs":            logs,
            }
    except Exception as exc:
        logs.append(f"[ConsistencyAgent] LLM error: {exc} → assume pass")

    return {"consistency_passed": True, "agent_logs": logs}
