"""
批量评估脚本
运行方式：python evaluation/run_eval.py [--output logs/eval_result.csv]
"""
import sys, os, json, time, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from pathlib import Path

from storyweaver.game_session import GameSession
from storyweaver.agents.intent_agent import run_intent_agent
from storyweaver.schemas import get_initial_state
from evaluation.metrics import (
    coherence_score,
    branch_diversity,
    intent_accuracy,
    consistency_accuracy,
    latency_stats,
)

TEST_CASES_PATH = Path("data/test_cases/eval_inputs.json")
LOGS_DIR        = Path("logs")


def load_test_cases() -> dict:
    with open(TEST_CASES_PATH, encoding="utf-8") as f:
        return json.load(f)


def run_intent_eval(cases: list[dict]) -> dict:
    print("\n[1/4] 意图识别准确率评估...")

    def classify(text: str) -> str:
        dummy_state = {
            "player_input": text, "agent_logs": [],
            "inventory": [], "npcs_status": {}, "plot_flags": {},
        }
        result = run_intent_agent(dummy_state)
        return result.get("intent", "OTHER")

    result = intent_accuracy(cases, classify)
    print(f"  ✓ 准确率：{result['accuracy']:.2%}  ({sum(r['correct'] for r in result['details'])}/{len(cases)})")
    return result


def run_consistency_eval(cases: list[dict]) -> dict:
    print("\n[2/4] 一致性检测准确率评估...")
    from storyweaver.agents.consistency_agent import run_consistency_agent
    from storyweaver.agents.intent_agent import run_intent_agent

    def check(text: str, base_state: dict) -> dict:
        # 先用 intent_agent 提取真实意图和实体，避免写死 USE_ITEM
        intent_state = {
            "player_input": text, "agent_logs": [],
            "inventory": base_state.get("inventory", []),
            "npcs_status": base_state.get("npcs_status", {}),
            "plot_flags": base_state.get("plot_flags", {}),
        }
        intent_result = run_intent_agent(intent_state)
        state = {
            "player_input": text,
            "intent":       intent_result.get("intent", "OTHER"),
            "entities":     intent_result.get("entities", {}),
            "inventory":    base_state.get("inventory", []),
            "npcs_status":  base_state.get("npcs_status", {}),
            "plot_flags":   base_state.get("plot_flags", {}),
            "player_location": base_state.get("player_location", "华州·破旧客栈"),
            "companion_relation": base_state.get("companion_relation", 20),
            "silver":       base_state.get("silver", 15),
            "turn_history": [],
            "agent_logs":   [],
        }
        return run_consistency_agent(state)

    result = consistency_accuracy(cases, check)
    print(f"  ✓ 准确率：{result['accuracy']:.2%}  ({sum(r['correct'] for r in result['details'])}/{len(cases)})")
    return result


def run_game_flow_eval(cases: list[dict]) -> tuple[list, list, list]:
    """跑完整游戏回合，收集延迟 / 连贯性 / 选项差异度数据。"""
    print("\n[3/4] 完整游戏流程评估...")
    session     = GameSession()
    latencies:  list[float] = []
    diversities: list[float] = []
    cohesion_scores: list[float] = []
    rows        = []

    for i, tc in enumerate(cases):
        print(f"  case {i+1}/{len(cases)}: {tc['input'][:30]}…", end=" ", flush=True)
        try:
            session.new_game()

            # 可选前置步骤
            for step in tc.get("setup_steps", []):
                session.step(step)

            t0     = time.time()
            result = session.step(tc["input"])
            elapsed = (time.time() - t0) * 1000
            latencies.append(elapsed)

            choices  = result.get("next_choices", [])
            div      = branch_diversity(choices)
            diversities.append(div)

            state    = session.get_state()
            history  = state.get("turn_history", []) if state else []
            coh      = coherence_score(history) if len(history) >= 2 else 5.0
            cohesion_scores.append(coh)

            rows.append({
                "input":             tc["input"],
                "latency_ms":        round(elapsed, 1),
                "num_choices":       len(choices),
                "branch_diversity":  div,
                "coherence_score":   coh,
                "consistency_passed": result.get("consistency_passed", True),
                "narration_len":     len(result.get("narration", "")),
            })
            print(f"✓  latency={elapsed:.0f}ms  div={div:.2f}  coh={coh:.1f}")

        except Exception as exc:
            print(f"✗ ERROR: {exc}")
            rows.append({"input": tc["input"], "error": str(exc)})

    return rows, latencies, diversities


def run_evaluation(output_csv: str = "logs/eval_result.csv"):
    LOGS_DIR.mkdir(exist_ok=True)
    cases = load_test_cases()

    intent_cases      = cases.get("intent_cases", [])
    consistency_cases = cases.get("consistency_cases", [])
    flow_cases        = cases.get("flow_cases", [])

    # ── 1. 意图识别 ──────────────────────────────────────────────────────────
    intent_result = run_intent_eval(intent_cases) if intent_cases else {"accuracy": 0}

    # ── 2. 一致性检测 ────────────────────────────────────────────────────────
    consist_result = run_consistency_eval(consistency_cases) if consistency_cases else {"accuracy": 0}

    # ── 3. 完整流程 ──────────────────────────────────────────────────────────
    flow_rows, latencies, diversities = (
        run_game_flow_eval(flow_cases) if flow_cases else ([], [], [])
    )

    # ── 4. 汇总统计 ──────────────────────────────────────────────────────────
    lat_stats = latency_stats(latencies)
    print("\n[4/4] 汇总统计")
    print(f"  意图识别准确率：{intent_result['accuracy']:.2%}")
    print(f"  一致性检测准确率：{consist_result['accuracy']:.2%}")
    if latencies:
        print(f"  响应延迟：mean={lat_stats['mean']}ms  P50={lat_stats['p50']}ms  P90={lat_stats['p90']}ms")
    if diversities:
        import statistics
        print(f"  选项差异度：avg={statistics.mean(diversities):.3f}")

    # ── 保存结果 ─────────────────────────────────────────────────────────────
    if flow_rows:
        df = pd.DataFrame(flow_rows)
        df.to_csv(output_csv, index=False, encoding="utf-8-sig")
        print(f"\n✓ 详细结果已保存至：{output_csv}")

    # 保存汇总 JSON
    summary = {
        "intent_accuracy":       intent_result["accuracy"],
        "consistency_accuracy":  consist_result["accuracy"],
        "latency_ms":            lat_stats,
        "avg_branch_diversity":  round(sum(diversities)/len(diversities), 4) if diversities else 0,
    }
    summary_path = LOGS_DIR / "eval_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"✓ 汇总指标已保存至：{summary_path}")

    return summary


def _extract_item(text: str) -> str:
    for item in ["干粮", "碎银", "匕首", "药材", "委托书", "布条", "玉牌"]:
        if item in text:
            return item
    return ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="logs/eval_result.csv")
    args = parser.parse_args()
    run_evaluation(args.output)
