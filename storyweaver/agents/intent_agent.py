"""
IntentAgent — NLU 意图识别
规则优先，低置信度时回退到 DeepSeek JSON 分类。
"""
import json
from storyweaver.config import get_client, MODEL, INTENT_TEMPERATURE
from storyweaver.schemas import GameState
from prompts.intent_prompts import INTENT_CLASSIFY_PROMPT

# ── 关键词规则表 ───────────────────────────────────────────────────────────────
INTENT_KEYWORDS: dict[str, list[str]] = {
    "PROTECT":     ["保护", "护着", "守护", "挡在", "庇护", "护住", "挡住", "拦住"],
    "NEGOTIATE":   ["谈", "交涉", "商量", "说和", "谈判", "交谈", "打招呼", "问候", "搭话", "商议", "点头示意", "质问", "换取", "说服"],
    "INVESTIGATE": ["探", "查", "观察", "四处", "搜寻", "察看", "打量", "窥探", "审视",
                    "细看", "仔细", "打探", "张望", "摸走", "暗中"],
    "HELP":        ["帮", "救", "接济", "施舍", "援手", "相助", "搭把手", "给食", "分给", "施粮"],
    "DECEIVE":     ["骗", "谎称", "假装", "欺瞒", "谎说", "蒙混", "伪装", "假称", "冒充"],
    "FLEE":        ["跑", "逃", "溜", "躲", "撤离", "逃走", "撒腿", "退走", "离开"],
    "REST":        ["歇", "休息", "打尖", "睡", "歇脚", "停下", "过夜", "养神", "闭目"],
    "ASK":         ["问", "询问", "打听", "请教", "请问", "询", "追问"],
    "USE_ITEM":    ["使用", "递上", "包扎", "服下", "掏出", "敷药", "递给"],
    "BRIBE":       ["打点", "贿赂", "送钱", "塞钱", "银子", "铜钱"],
    "FIGHT":       ["打", "杀", "拼", "动手", "出拳", "亮刀", "拔刀", "刀", "砍", "亮出"],
}

NPC_NAMES     = ["穗", "舌头", "花儿", "月儿", "冬梅", "托主", "豚妖", "官兵", "流民", "商人", "店主"]
LOCATION_NAMES = ["华州", "阌乡", "崤山", "洛阳", "客栈", "官道", "山道", "城门", "渡口", "集市"]
ITEM_NAMES    = ["干粮", "碎银", "委托书", "匕首", "药材", "香袋", "布条", "玉牌", "通关文牒"]


def _extract_entities(text: str) -> dict:
    entities: dict = {}
    for name in NPC_NAMES:
        if name in text:
            entities["target_npc"] = name
            break
    for loc in LOCATION_NAMES:
        if loc in text:
            entities["target_location"] = loc
            break
    for item in ITEM_NAMES:
        if item in text:
            entities["item_name"] = item
            break
    return entities


def run_intent_agent(state: GameState) -> dict:
    player_input = state.get("player_input", "")
    logs         = list(state.get("agent_logs", []))

    # ── 规则层 ─────────────────────────────────────────────────────────────
    scores: dict[str, int] = {intent: 0 for intent in INTENT_KEYWORDS}
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in player_input:
                scores[intent] += len(kw)   # longer match = higher weight

    best_intent = max(scores, key=lambda k: scores[k])
    best_score  = scores[best_intent]

    if best_score > 0:
        confidence = min(0.55 + best_score * 0.12, 0.95)
        logs.append(f"[IntentAgent] rule → {best_intent} (score={best_score}, conf={confidence:.2f})")
        return {
            "intent":            best_intent,
            "entities":          _extract_entities(player_input),
            "intent_confidence": confidence,
            "agent_logs":        logs,
        }

    # ── LLM 回退层 ─────────────────────────────────────────────────────────
    return _llm_classify(player_input, logs)


def _llm_classify(player_input: str, logs: list) -> dict:
    client = get_client()
    prompt = INTENT_CLASSIFY_PROMPT.format(player_input=player_input)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=INTENT_TEMPERATURE,
            response_format={"type": "json_object"},
            max_tokens=200,
        )
        result = json.loads(resp.choices[0].message.content)
        intent     = result.get("intent", "OTHER")
        confidence = float(result.get("confidence", 0.8))
        entities   = result.get("entities", {})
        logs.append(f"[IntentAgent] LLM → {intent} (conf={confidence:.2f})")
        return {
            "intent":            intent,
            "entities":          {k: v for k, v in entities.items() if v},
            "intent_confidence": confidence,
            "agent_logs":        logs,
        }
    except Exception as exc:
        logs.append(f"[IntentAgent] LLM error: {exc} → fallback OTHER")
        return {
            "intent":            "OTHER",
            "entities":          _extract_entities(player_input),
            "intent_confidence": 0.3,
            "agent_logs":        logs,
        }
