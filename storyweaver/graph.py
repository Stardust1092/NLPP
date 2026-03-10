"""
LangGraph 图定义 — StoryWeaver 多 Agent 状态机
节点顺序：intent → consistency → (repair|narrator) → world → choice
"""
from langgraph.graph import StateGraph, END
from storyweaver.schemas import GameState
from storyweaver.agents import (
    run_intent_agent,
    run_consistency_agent,
    run_repair_agent,
    run_narrator_agent,
    run_world_agent,
    run_choice_agent,
)


def _route_after_consistency(state: GameState) -> str:
    """一致性检查通过 → narrator；失败 → repair。"""
    return "narrator" if state.get("consistency_passed", True) else "repair"


def build_graph():
    """构建并编译 LangGraph 状态图。"""
    g = StateGraph(GameState)

    # ── 注册节点 ───────────────────────────────────────────────────────────
    g.add_node("intent",      run_intent_agent)
    g.add_node("consistency", run_consistency_agent)
    g.add_node("repair",      run_repair_agent)
    g.add_node("narrator",    run_narrator_agent)
    g.add_node("world",       run_world_agent)
    g.add_node("choice",      run_choice_agent)

    # ── 边定义 ────────────────────────────────────────────────────────────
    g.set_entry_point("intent")
    g.add_edge("intent", "consistency")
    g.add_conditional_edges(
        "consistency",
        _route_after_consistency,
        {"narrator": "narrator", "repair": "repair"},
    )
    g.add_edge("repair",   "narrator")   # repair 后仍需生成后续选项
    g.add_edge("narrator", "world")
    g.add_edge("world",    "choice")
    g.add_edge("choice",   END)

    return g.compile()


# 单例，避免重复编译
_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
