from typing import TypedDict, Optional
from pydantic import BaseModel


class GameState(TypedDict):
    # ── 玩家输入 ──────────────────────────────────────────────────────────────
    player_input: str
    turn_id: int

    # ── NLU 输出 ──────────────────────────────────────────────────────────────
    intent: str          # PROTECT/NEGOTIATE/INVESTIGATE/HELP/DECEIVE/FLEE/REST/ASK/USE_ITEM/BRIBE/FIGHT/OTHER
    entities: dict       # {target_npc, target_location, item_name}
    intent_confidence: float

    # ── 叙事状态 ──────────────────────────────────────────────────────────────
    player_name: str           # 良
    current_act: int           # 1-4（华州/阌乡/崤山/洛阳）
    player_location: str
    companion_relation: int    # 穗对主角的信任度 0-100
    reputation: int            # 名声 -50~+50
    silver: int                # 铜钱数量
    inventory: list            # ["干粮×2", "委托书", ...]
    npcs_status: dict          # {npc_name: {alive, location, relation, revealed_info}}
    locations_visited: list
    plot_flags: dict           # 关键道德选择记录
    revealed_backstory: list   # 已揭露的暗线碎片
    turn_history: list         # 最近8轮 [{turn_id, player_input, intent, narration, choices_offered}]

    # ── 一致性检查 ────────────────────────────────────────────────────────────
    consistency_passed: bool
    consistency_violation: str
    repair_suggestion: str

    # ── 输出 ──────────────────────────────────────────────────────────────────
    narration: str
    dialogue: dict             # {speaker: str, text: str}，可为空 {}
    backstory_fragment: str    # 本轮释放的暗线碎片，可为空 ""
    next_choices: list         # 3-4 个选项
    state_delta: dict          # 本轮状态变更

    # ── 元信息 ────────────────────────────────────────────────────────────────
    agent_logs: list
    latency_ms: float


class StoryOutput(BaseModel):
    narration: str
    dialogue: Optional[dict] = None
    backstory_fragment: Optional[str] = None
    next_choices: list[str]
    state_delta: dict
    agent_logs: list[str] = []
    latency_ms: float = 0.0
    consistency_passed: bool = True
    repair_suggestion: Optional[str] = None


def get_initial_state(scenario: dict) -> GameState:
    """从场景 JSON 构建初始 GameState。"""
    init = scenario["initial_state"]
    return GameState(
        player_input="",
        turn_id=0,
        intent="START",
        entities={},
        intent_confidence=1.0,
        player_name=init["player_name"],
        current_act=init["current_act"],
        player_location=init["player_location"],
        companion_relation=init["companion_relation"],
        reputation=init["reputation"],
        silver=init["silver"],
        inventory=list(init["inventory"]),
        npcs_status={k: dict(v) for k, v in init["npcs_status"].items()},
        locations_visited=list(init["locations_visited"]),
        plot_flags=dict(init["plot_flags"]),
        revealed_backstory=[],
        turn_history=[],
        consistency_passed=True,
        consistency_violation="",
        repair_suggestion="",
        narration=scenario.get("opening_narration", ""),
        dialogue={},
        backstory_fragment="",
        next_choices=list(scenario.get("initial_choices", [])),
        state_delta={},
        agent_logs=[],
        latency_ms=0.0,
    )
