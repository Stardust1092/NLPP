import json
from storyweaver.schemas import GameState


def build_narrator_prompt(state: GameState) -> str:
    """构建旁白生成 prompt，包含当前状态摘要和历史。"""

    relation       = state.get("companion_relation", 50)
    location       = state.get("player_location", "未知")
    silver         = state.get("silver", 0)
    inventory      = state.get("inventory", [])
    plot_flags     = state.get("plot_flags", {})
    current_act    = state.get("current_act", 1)
    player_input   = state.get("player_input", "")
    intent         = state.get("intent", "OTHER")
    entities       = state.get("entities", {})
    backstory_done = state.get("revealed_backstory", [])
    npcs_status    = state.get("npcs_status", {})

    # ── 状态摘要 ────────────────────────────────────────────────────────────
    # NPC 在场情况
    present_npcs = [
        name for name, info in npcs_status.items()
        if info.get("alive", True) and location in info.get("location", "")
    ]

    state_summary = f"""当前游戏状态：
- 地点：{location}（第{current_act}幕）
- 穗的信任度：{relation}/100
- 铜钱：{silver} 文
- 背包：{', '.join(inventory) if inventory else '空'}
- 在场人物：{', '.join(present_npcs) if present_npcs else '无'}
- 关键标记：{json.dumps({k: v for k, v in plot_flags.items() if v}, ensure_ascii=False)}
- 已释放暗线数：{len(backstory_done)} 条"""

    # ── 近期历史 ────────────────────────────────────────────────────────────
    history     = state.get("turn_history", [])[-3:]
    history_text = "（旅途起点，无历史记录）"
    if history:
        lines = []
        for t in history:
            narr_preview = t.get("narration", "")[:40]
            lines.append(f"  第{t.get('turn_id','?')}轮：玩家「{t.get('player_input','')}」→ {narr_preview}…")
        history_text = "\n".join(lines)

    # ── 一致性修复注记 ───────────────────────────────────────────────────────
    consistency_note = ""
    if not state.get("consistency_passed", True):
        consistency_note = (
            f"\n⚠ 一致性修复提示：{state.get('repair_suggestion', '')}\n"
            "请在旁白中自然呈现修复内容，不要直接说「错误」。\n"
        )

    # ── 暗线释放指引 ─────────────────────────────────────────────────────────
    backstory_hint = ""
    if relation > 70 and len(backstory_done) < 5:
        backstory_hint = "（穗信任度已超70，本轮可释放一条暗线碎片，揭示委托背后的线索）"
    elif relation < 30:
        backstory_hint = "（穗信任度低于30，本轮不释放任何暗线碎片，穗保持沉默警惕）"

    prompt = f"""根据以下游戏状态，生成本回合的旁白。

{state_summary}

近期旅途经历：
{history_text}
{consistency_note}
本轮玩家行动：「{player_input}」
解析意图：{intent}
涉及实体：{json.dumps(entities, ensure_ascii=False)}
{backstory_hint}

请严格按照 system prompt 中的 JSON 格式输出，确保：
1. narration 准确反映玩家行动「{player_input}」及其后果
2. 若有对话发生，dialogue 中填写说话者和内容；穗只能通过布条表达
3. state_delta 准确记录本回合带来的所有状态变化
4. 选择对旁白风格有益的暗线碎片时机，不强行插入"""

    return prompt
