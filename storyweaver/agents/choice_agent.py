"""
ChoiceAgent — 差异化选项生成
生成 3-4 个方向各异的行动选项，确保不同选项导向实质不同后果。
"""
import json
from storyweaver.config import get_client, MODEL, CHOICE_TEMPERATURE
from storyweaver.schemas import GameState
from prompts.choice_prompts import CHOICE_GENERATION_PROMPT

# 每种意图对应的默认后备选项
FALLBACK_CHOICES: dict[int, list[str]] = {
    1: ["向穗点头，示意无意伤害她们", "找舌头商议前路", "出门打探消息", "取出委托书再细看"],
    2: ["帮月儿擦干眼泪，安慰她", "向阌乡渡口官兵打听路况", "在集市购买干粮", "警惕地观察四周"],
    3: ["护着孩子们紧紧跟随", "绕山间小路避开官道", "与遇到的义军斥候交涉", "在山洞暂避休息"],
    4: ["护着孩子们快速穿过城门", "向穗询问目的地确切位置", "暗中观察那户富贵人家", "寻一处安全落脚点"],
}


def run_choice_agent(state: GameState) -> dict:
    client = get_client()
    logs   = list(state.get("agent_logs", []))

    narration        = state.get("narration", "")
    location         = state.get("player_location", "")
    current_act      = state.get("current_act", 1)
    companion_relation = state.get("companion_relation", 50)
    inventory        = state.get("inventory", [])
    plot_flags       = state.get("plot_flags", {})

    # 获取上轮选项，避免重复
    last_choices: list[str] = []
    turn_history = state.get("turn_history", [])
    if turn_history:
        last_choices = turn_history[-1].get("choices_offered", [])

    prompt = CHOICE_GENERATION_PROMPT.format(
        location           = location,
        current_act        = current_act,
        narration_summary  = narration[:60] + ("…" if len(narration) > 60 else ""),
        companion_relation = companion_relation,
        inventory          = ", ".join(inventory) if inventory else "空",
        plot_flags         = json.dumps(
            {k: v for k, v in plot_flags.items() if v}, ensure_ascii=False
        ),
        last_choices       = json.dumps(last_choices, ensure_ascii=False),
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=CHOICE_TEMPERATURE,
            response_format={"type": "json_object"},
            max_tokens=350,
        )
        result  = json.loads(resp.choices[0].message.content)
        choices = result.get("choices", [])[:4]
        if len(choices) < 2:
            raise ValueError("too few choices generated")

        logs.append(f"[ChoiceAgent] {len(choices)} choices generated")
        return {"next_choices": choices, "agent_logs": logs}

    except Exception as exc:
        logs.append(f"[ChoiceAgent] error: {exc} → using fallback")
        fallback = FALLBACK_CHOICES.get(current_act, FALLBACK_CHOICES[1])
        # Filter out last_choices to ensure some novelty
        fallback = [c for c in fallback if c not in last_choices] or fallback
        return {"next_choices": fallback[:4], "agent_logs": logs}
