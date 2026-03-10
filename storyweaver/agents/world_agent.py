"""
WorldAgent — 世界状态更新
解析 state_delta，更新数值/道具/NPC/地点/plot_flags，
追加 turn_history，检测幕次切换。
"""
from storyweaver.schemas import GameState

# 地点 → 幕次映射
LOCATION_ACT: dict[str, int] = {
    "华州":          1, "华州·城内":   1, "华州·城外":   1, "华州·破旧客栈": 1,
    "阌乡":          2, "阌乡·渡口":   2, "阌乡·集市":   2, "阌乡·客栈":    2,
    "崤山":          3, "崤山·官道":   3, "崤山·密林":   3, "崤山·山寨":    3,
    "洛阳":          4, "洛阳·城门":   4, "洛阳·内城":   4, "洛阳·福王府附近": 4,
}


def run_world_agent(state: GameState) -> dict:
    logs = list(state.get("agent_logs", []))
    delta = state.get("state_delta") or {}

    companion_relation = state.get("companion_relation", 50)
    reputation         = state.get("reputation",  0)
    silver             = state.get("silver",       15)
    inventory          = list(state.get("inventory", []))
    npcs_status        = {k: dict(v) for k, v in state.get("npcs_status", {}).items()}
    locations_visited  = list(state.get("locations_visited", []))
    plot_flags         = dict(state.get("plot_flags", {}))
    revealed_backstory = list(state.get("revealed_backstory", []))
    turn_history       = list(state.get("turn_history", []))
    current_act        = state.get("current_act", 1)
    player_location    = state.get("player_location", "华州·破旧客栈")

    # ── 应用数值变化 ───────────────────────────────────────────────────────
    companion_relation = max(0, min(100, companion_relation + delta.get("companion_relation_change", 0)))
    reputation         = max(-50, min(50, reputation         + delta.get("reputation_change",         0)))
    silver             = max(0,           silver             + delta.get("silver_change",              0))

    # ── 道具更新 ───────────────────────────────────────────────────────────
    for item in delta.get("inventory_add", []):
        if item and item not in inventory:
            inventory.append(item)
    for item in delta.get("inventory_remove", []):
        if item in inventory:
            inventory.remove(item)

    # ── 地点更新 ───────────────────────────────────────────────────────────
    new_loc = delta.get("new_location", "")
    if new_loc and new_loc != player_location:
        player_location = new_loc
        logs.append(f"[WorldAgent] location → {new_loc}")

    for loc in delta.get("locations_add", []):
        if loc and loc not in locations_visited:
            locations_visited.append(loc)

    if player_location not in locations_visited:
        locations_visited.append(player_location)

    # ── 幕次检测 ───────────────────────────────────────────────────────────
    for loc_key, act_num in LOCATION_ACT.items():
        if loc_key in player_location and act_num != current_act:
            current_act = act_num
            logs.append(f"[WorldAgent] act transition → Act {current_act}")
            break

    # ── plot_flags 更新 ────────────────────────────────────────────────────
    for flag, val in delta.get("flags_set", {}).items():
        plot_flags[flag] = val

    # ── NPC 状态更新 ───────────────────────────────────────────────────────
    for npc_name, updates in delta.get("npc_updates", {}).items():
        if npc_name in npcs_status:
            npcs_status[npc_name].update(updates)

    # ── 暗线碎片追加 ──────────────────────────────────────────────────────
    frag = state.get("backstory_fragment", "")
    if frag and frag not in revealed_backstory:
        revealed_backstory.append(frag)
        logs.append("[WorldAgent] backstory fragment added")

    # ── turn_history 追加（保留最近8轮）────────────────────────────────────
    turn_record = {
        "turn_id":           state.get("turn_id", 0),
        "player_input":      state.get("player_input", ""),
        "intent":            state.get("intent", ""),
        "narration":         state.get("narration", "")[:80],
        "choices_offered":   state.get("next_choices", []),
        "companion_relation": companion_relation,
        "reputation":        reputation,
    }
    turn_history.append(turn_record)
    if len(turn_history) > 8:
        turn_history = turn_history[-8:]

    logs.append(
        f"[WorldAgent] relation={companion_relation} rep={reputation} silver={silver} act={current_act}"
    )

    return {
        "companion_relation": companion_relation,
        "reputation":         reputation,
        "silver":             silver,
        "inventory":          inventory,
        "npcs_status":        npcs_status,
        "locations_visited":  locations_visited,
        "plot_flags":         plot_flags,
        "revealed_backstory": revealed_backstory,
        "turn_history":       turn_history,
        "current_act":        current_act,
        "player_location":    player_location,
        "agent_logs":         logs,
    }
