"""
GameSession — 对外接口
管理单局游戏的完整状态，提供 new_game() 和 step() 两个核心方法。
"""
import json
import time
from datetime import datetime
from pathlib import Path

from storyweaver.schemas import GameState, get_initial_state
from storyweaver.graph import get_graph

SCENARIOS_DIR = Path(__file__).parent.parent / "data" / "scenarios"
LOGS_DIR      = Path(__file__).parent.parent / "logs"


class GameSession:
    def __init__(self):
        self._graph      = get_graph()
        self.state: GameState | None = None
        self.session_id  = ""
        LOGS_DIR.mkdir(exist_ok=True)

    # ── 公共接口 ──────────────────────────────────────────────────────────

    def new_game(self, scenario_name: str = "act1_huazhou") -> dict:
        """加载场景，初始化状态，返回开局信息（不走 Pipeline）。"""
        scenario_path = SCENARIOS_DIR / f"{scenario_name}.json"
        if not scenario_path.exists():
            raise FileNotFoundError(f"Scenario not found: {scenario_path}")

        with open(scenario_path, encoding="utf-8") as f:
            scenario = json.load(f)

        self.state      = get_initial_state(scenario)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        self._log_turn("【新游戏开始】", self.state)

        return {
            "narration":          self.state["narration"],
            "dialogue":           self.state["dialogue"],
            "backstory_fragment": self.state["backstory_fragment"],
            "next_choices":       self.state["next_choices"],
            "state_delta":        {},
            "agent_logs":         ["[GameSession] New game started"],
            "latency_ms":         0.0,
            "consistency_passed": True,
            "repair_suggestion":  "",
        }

    def step(self, player_input: str) -> dict:
        """执行一个游戏回合，完整走完 LangGraph Pipeline。"""
        if self.state is None:
            raise RuntimeError("Call new_game() before step()")

        self.state["player_input"] = player_input
        self.state["turn_id"]      = self.state.get("turn_id", 0) + 1

        t0           = time.time()
        result_state = self._graph.invoke(self.state)
        elapsed      = (time.time() - t0) * 1000

        self.state = result_state
        self._log_turn(player_input, result_state)

        return {
            "narration":          result_state.get("narration", ""),
            "dialogue":           result_state.get("dialogue", {}),
            "backstory_fragment": result_state.get("backstory_fragment", ""),
            "next_choices":       result_state.get("next_choices", []),
            "state_delta":        result_state.get("state_delta", {}),
            "agent_logs":         result_state.get("agent_logs", []),
            "latency_ms":         elapsed,
            "consistency_passed": result_state.get("consistency_passed", True),
            "repair_suggestion":  result_state.get("repair_suggestion", ""),
        }

    def get_state(self) -> GameState | None:
        return self.state

    # ── 内部工具 ──────────────────────────────────────────────────────────

    def _log_turn(self, player_input: str, state: GameState) -> None:
        log_file = LOGS_DIR / f"session_{self.session_id}.jsonl"
        record   = {
            "ts":                  datetime.now().isoformat(),
            "turn_id":             state.get("turn_id", 0),
            "player_input":        player_input,
            "intent":              state.get("intent", ""),
            "intent_confidence":   state.get("intent_confidence", 0.0),
            "consistency_passed":  state.get("consistency_passed", True),
            "narration":           state.get("narration", ""),
            "next_choices":        state.get("next_choices", []),
            "companion_relation":  state.get("companion_relation", 0),
            "reputation":          state.get("reputation",  0),
            "silver":              state.get("silver",       0),
            "current_act":         state.get("current_act",  1),
            "plot_flags":          state.get("plot_flags",  {}),
            "latency_ms":          state.get("latency_ms",  0.0),
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
