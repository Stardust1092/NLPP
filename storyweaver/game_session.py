"""
GameSession — 对外接口
管理单局游戏的完整状态，提供 new_game() 和 step() 两个核心方法。

执行策略：
  - intent / consistency / repair / world 顺序执行（均为纯规则，毫秒级）
  - narrator 与 choice 并行执行（均为 LLM 调用，各约 15s）
    → 实际延迟从 ~30s 降至 ~15s
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from storyweaver.schemas import GameState, get_initial_state
from storyweaver.graph import get_graph
from storyweaver.agents import (
    run_intent_agent,
    run_consistency_agent,
    run_repair_agent,
    run_narrator_agent,
    stream_narrator_agent,
    run_world_agent,
    run_choice_agent,
)

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
        """执行一个游戏回合。

        执行顺序：
          1. intent + consistency (+ repair)  —— 纯规则，顺序，毫秒级
          2. narrator ∥ choice               —— LLM 并行，节省 ~15s
          3. world                            —— 纯规则，顺序，依赖 narrator 的 state_delta
        """
        if self.state is None:
            raise RuntimeError("Call new_game() before step()")

        # 复制状态，避免并行写入时的竞争
        state = dict(self.state)
        state["player_input"] = player_input
        state["turn_id"]      = state.get("turn_id", 0) + 1

        t0 = time.time()

        # ── 阶段 1：顺序执行规则 Agent ────────────────────────────────────
        state.update(run_intent_agent(state))
        state.update(run_consistency_agent(state))
        if not state.get("consistency_passed", True):
            state.update(run_repair_agent(state))

        # ── 阶段 2：并行执行两个 LLM Agent ───────────────────────────────
        # narrator 和 choice 各自读入当前 state 的快照，互不影响
        with ThreadPoolExecutor(max_workers=2) as pool:
            narrator_future = pool.submit(run_narrator_agent, dict(state))
            choice_future   = pool.submit(run_choice_agent,   dict(state))
            narrator_result = narrator_future.result()
            choice_result   = choice_future.result()

        state.update(narrator_result)   # 写入 narration / state_delta 等
        state.update(choice_result)     # 写入 next_choices
        # 合并两份 agent_logs（避免其中一份覆盖另一份）
        state["agent_logs"] = narrator_result.get("agent_logs", []) + \
                              choice_result.get("agent_logs", [])

        # ── 阶段 3：world 依赖 narrator 的 state_delta，顺序执行 ──────────
        state.update(run_world_agent(state))

        elapsed        = (time.time() - t0) * 1000
        state["latency_ms"] = elapsed
        self.state     = state
        self._log_turn(player_input, state)

        return {
            "narration":          state.get("narration", ""),
            "dialogue":           state.get("dialogue", {}),
            "backstory_fragment": state.get("backstory_fragment", ""),
            "next_choices":       state.get("next_choices", []),
            "state_delta":        state.get("state_delta", {}),
            "agent_logs":         state.get("agent_logs", []),
            "latency_ms":         elapsed,
            "consistency_passed": state.get("consistency_passed", True),
            "repair_suggestion":  state.get("repair_suggestion", ""),
        }

    def stream_step(self, player_input: str):
        """流式回合：叙事文本逐 token 推送，选项在后台并行生成。

        Yields:
            {"type": "chunk",  "text": str}   — 叙事文本片段
            {"type": "final",  "result": dict} — 完整结果（含 dialogue/choices/状态）
        """
        if self.state is None:
            raise RuntimeError("Call new_game() before stream_step()")

        state = dict(self.state)
        state["player_input"] = player_input
        state["turn_id"]      = state.get("turn_id", 0) + 1

        t0 = time.time()

        # ── 阶段 1：规则 Agent（顺序，毫秒级）────────────────────────────
        state.update(run_intent_agent(state))
        state.update(run_consistency_agent(state))
        if not state.get("consistency_passed", True):
            state.update(run_repair_agent(state))

        # ── 阶段 2：choice 后台线程 + narrator 流式输出（并行）────────────
        # choice 在独立线程里跑，不阻塞主线程的流式输出
        with ThreadPoolExecutor(max_workers=1) as pool:
            choice_future = pool.submit(run_choice_agent, dict(state))

            # 主线程：流式输出叙事文本
            for event in stream_narrator_agent(state):
                if event["type"] == "chunk":
                    yield {"type": "chunk", "text": event["text"]}
                elif event["type"] == "done":
                    state.update(event["result"])

            # narrator 流结束后等待 choice（通常已完成）
            choice_result = choice_future.result()

        state.update(choice_result)
        state["agent_logs"] = (state.get("agent_logs") or []) + \
                              (choice_result.get("agent_logs") or [])

        # ── 阶段 3：world（顺序，依赖 narrator 的 state_delta）────────────
        state.update(run_world_agent(state))

        elapsed           = (time.time() - t0) * 1000
        state["latency_ms"] = elapsed
        self.state        = state
        self._log_turn(player_input, state)

        yield {
            "type": "final",
            "result": {
                "narration":          state.get("narration", ""),
                "dialogue":           state.get("dialogue", {}),
                "backstory_fragment": state.get("backstory_fragment", ""),
                "next_choices":       state.get("next_choices", []),
                "state_delta":        state.get("state_delta", {}),
                "agent_logs":         state.get("agent_logs", []),
                "latency_ms":         elapsed,
                "consistency_passed": state.get("consistency_passed", True),
                "repair_suggestion":  state.get("repair_suggestion", ""),
            },
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
