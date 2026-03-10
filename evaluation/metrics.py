"""
评估指标模块
1. coherence_score       — LLM-as-judge 叙事连贯性（0-5）
2. branch_diversity      — 选项差异度（BLEU 逆差）
3. intent_accuracy       — 意图识别准确率
4. consistency_accuracy  — 一致性检测准确率
5. latency_stats         — P50/P90 响应延迟
"""
from __future__ import annotations
import json
import statistics
from typing import Callable

from storyweaver.config import get_client, MODEL


# ── 1. 叙事连贯性（LLM 评分）─────────────────────────────────────────────────

def coherence_score(turn_history: list[dict]) -> float:
    """
    用 DeepSeek 评判最近 3 轮旁白的叙事连贯性，返回 0-5 分。
    """
    recent = turn_history[-3:] if len(turn_history) >= 2 else turn_history
    if not recent:
        return 5.0

    story_text = "\n".join(
        f"[{i+1}] {t.get('narration', '')}"
        for i, t in enumerate(recent)
    )

    prompt = (
        f"请评估以下明末文字冒险游戏段落的叙事连贯性（人物、地点、逻辑是否前后一致），"
        f"打分 0-5（5 分最高）。\n\n{story_text}\n\n"
        f"只返回一个数字（0-5 的浮点数），不要其他内容。"
    )

    try:
        client = get_client()
        resp   = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=10,
        )
        return float(resp.choices[0].message.content.strip())
    except Exception:
        return 3.0


# ── 2. 选项差异度 ─────────────────────────────────────────────────────────────

def branch_diversity(choices: list[str]) -> float:
    """
    计算一组选项之间的平均 BLEU 差异度（越高越多样）。
    返回 0-1，数值越高说明选项越不重复。
    """
    if len(choices) < 2:
        return 1.0

    try:
        from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
        smooth = SmoothingFunction().method1

        similarities: list[float] = []
        for i in range(len(choices)):
            for j in range(i + 1, len(choices)):
                ref = [list(choices[i])]      # character-level
                hyp = list(choices[j])
                sim = sentence_bleu(ref, hyp, smoothing_function=smooth)
                similarities.append(sim)

        avg_sim = statistics.mean(similarities) if similarities else 0.0
        return round(1.0 - avg_sim, 4)       # 逆相似度 = 差异度

    except ImportError:
        # NLTK 未安装时，用简单字符重叠率
        total, count = 0.0, 0
        for i in range(len(choices)):
            for j in range(i + 1, len(choices)):
                a, b   = set(choices[i]), set(choices[j])
                overlap = len(a & b) / max(len(a | b), 1)
                total  += overlap
                count  += 1
        return round(1.0 - (total / count if count else 0.0), 4)


# ── 3. 意图识别准确率 ─────────────────────────────────────────────────────────

def intent_accuracy(test_cases: list[dict], classify_fn: Callable[[str], str]) -> dict:
    """
    test_cases: [{"input": "...", "expected_intent": "HELP"}, ...]
    classify_fn: 接受 player_input 字符串，返回 intent 字符串
    """
    correct = 0
    results = []
    for tc in test_cases:
        predicted = classify_fn(tc["input"])
        expected  = tc.get("expected_intent", "")
        match     = predicted == expected
        correct  += int(match)
        results.append({
            "input":    tc["input"],
            "expected": expected,
            "predicted": predicted,
            "correct":   match,
        })

    accuracy = correct / len(test_cases) if test_cases else 0.0
    return {"accuracy": round(accuracy, 4), "details": results}


# ── 4. 一致性检测准确率 ────────────────────────────────────────────────────────

def consistency_accuracy(test_cases: list[dict], check_fn: Callable) -> dict:
    """
    test_cases: [{"input": "...", "expected_passed": false, "setup_state": {}}, ...]
    check_fn: 接受 (player_input, state_dict) 返回 {"consistency_passed": bool}
    """
    correct = 0
    results = []
    for tc in test_cases:
        result   = check_fn(tc["input"], tc.get("setup_state", {}))
        passed   = result.get("consistency_passed", True)
        expected = tc.get("expected_passed", True)
        match    = (passed == expected)
        correct += int(match)
        results.append({
            "input":    tc["input"],
            "expected": expected,
            "actual":   passed,
            "correct":  match,
            "violation": result.get("consistency_violation", ""),
        })

    accuracy = correct / len(test_cases) if test_cases else 0.0
    return {"accuracy": round(accuracy, 4), "details": results}


# ── 5. 响应延迟统计 ───────────────────────────────────────────────────────────

def latency_stats(latencies: list[float]) -> dict:
    """计算 mean / P50 / P90 延迟（单位：ms）。"""
    if not latencies:
        return {"mean": 0, "p50": 0, "p90": 0}
    sorted_l = sorted(latencies)
    n        = len(sorted_l)
    p50_idx  = int(n * 0.50)
    p90_idx  = int(n * 0.90)
    return {
        "mean": round(statistics.mean(sorted_l), 1),
        "p50":  round(sorted_l[min(p50_idx, n-1)], 1),
        "p90":  round(sorted_l[min(p90_idx, n-1)], 1),
        "count": n,
    }
