"""
Gradio UI — StoryWeaver · 饿殍·明末千里行
双栏布局：左侧故事展示 + 右侧状态面板；底部选项按钮 + 自由输入框
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr
from storyweaver.game_session import GameSession

# ── 全局会话 ──────────────────────────────────────────────────────────────────
session       = GameSession()
_story_turns: list[str] = []

# ── CSS 样式（明末卷轴风）────────────────────────────────────────────────────
CUSTOM_CSS = """
/* ── 页面与容器 ─────────────────────────────────────── */
body, html { background: #0d0904 !important; }
gradio-app { background: #0d0904 !important; }
.gradio-container {
    width: 100% !important;
    max-width: 1200px !important;
    margin: 0 auto !important;
    background: #0d0904 !important;
    padding: 0 12px !important;
    box-sizing: border-box !important;
}
footer, .built-with { display: none !important; }

/* ── 标题区 ─────────────────────────────────────────── */
#app-header {
    background: linear-gradient(180deg, #1e1208 0%, #120c05 100%);
    border-bottom: 2px solid #6a4812;
    padding: 20px 0 14px;
    text-align: center;
    margin-bottom: 16px;
}
#app-header h1 {
    color: #e8c860;
    font-family: 'KaiTi', 'STKaiti', 'SimSun', serif;
    font-size: 2.0em;
    margin: 0;
    letter-spacing: 6px;
    text-shadow: 0 0 16px rgba(220,180,60,0.4);
}
#app-header p {
    color: #907850;
    font-size: 0.85em;
    margin: 6px 0 0;
    letter-spacing: 1px;
}

/* ── 故事卷轴区 ─────────────────────────────────────── */
#story-box {
    font-family: 'KaiTi', 'STKaiti', 'SimSun', serif;
    line-height: 2.1;
    background: linear-gradient(160deg, #3a2510 0%, #2c1c0a 50%, #301e0c 100%);
    color: #ead8a8;
    padding: 28px 36px;
    border-radius: 4px;
    border-top: 3px solid #9a6a20;
    border-left: 4px solid #7a5018;
    border-right: 1px solid #4a3010;
    border-bottom: 1px solid #4a3010;
    min-height: 520px;
    max-height: 580px;
    overflow-y: auto;
    font-size: 15px;
    box-shadow:
        inset 3px 0 14px rgba(0,0,0,0.35),
        0 4px 20px rgba(0,0,0,0.5);
    scroll-behavior: smooth;
}

/* 滚动条美化 */
#story-box::-webkit-scrollbar { width: 5px; }
#story-box::-webkit-scrollbar-track { background: #0d0804; }
#story-box::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #6a4012, #3a2208);
    border-radius: 2px;
}

/* ── 叙事文本块 ─────────────────────────────────────── */
.narration-block {
    color: #f0deb8;
    margin-bottom: 12px;
    text-indent: 2em;
    letter-spacing: 0.06em;
    text-shadow: 0 1px 2px rgba(0,0,0,0.4);
}

/* ── 对话行 ─────────────────────────────────────────── */
.dialogue-line {
    color: #eec868;
    padding: 7px 18px;
    border-left: 3px solid #8a6020;
    margin: 10px 0;
    background: rgba(138,96,32,0.10);
    border-radius: 0 4px 4px 0;
    letter-spacing: 0.04em;
}
.speaker-name {
    color: #f8d870;
    font-weight: bold;
    letter-spacing: 0.12em;
    margin-right: 3px;
}

/* ── 暗线回忆块 ─────────────────────────────────────── */
.backstory-block {
    color: #c0a0e0;
    background: rgba(80,40,140,0.14);
    padding: 12px 20px;
    border-left: 3px solid #6040a8;
    margin: 14px 0;
    border-radius: 0 6px 6px 0;
    font-style: italic;
    letter-spacing: 0.05em;
    line-height: 1.9;
}

/* ── 玩家行动标注 ───────────────────────────────────── */
.player-action {
    color: #7090b8;
    font-size: 0.88em;
    margin-bottom: 10px;
    padding-bottom: 7px;
    border-bottom: 1px dashed #243448;
    letter-spacing: 0.12em;
}

/* ── 幕次标题 ───────────────────────────────────────── */
.act-title {
    color: #d4a828;
    font-size: 0.96em;
    letter-spacing: 5px;
    text-align: center;
    margin: 20px 0 22px;
    padding: 8px 0;
    border-top: 1px solid #382810;
    border-bottom: 1px solid #382810;
    text-shadow: 0 0 10px rgba(200,155,40,0.35);
}

/* ── 修复提示 ───────────────────────────────────────── */
.repair-note {
    color: #d08080;
    font-size: 0.86em;
    background: rgba(150,50,50,0.12);
    padding: 8px 14px;
    border: 1px solid rgba(150,60,60,0.22);
    border-radius: 4px;
    margin: 8px 0;
}

/* ── 回合分割线 ─────────────────────────────────────── */
.turn-divider {
    border: none;
    border-top: 1px dashed #261a08;
    margin: 18px 0;
}

/* ── 空状态占位 ─────────────────────────────────────── */
.empty-hint {
    color: #c8a858;
    text-align: center;
    padding-top: 180px;
    font-size: 1.1em;
    letter-spacing: 3px;
    line-height: 2.8;
    text-shadow: 0 1px 4px rgba(0,0,0,0.6);
}

/* ── 选项按钮区标签 ─────────────────────────────────── */
.choice-label {
    color: #7a6030 !important;
    font-size: 0.82em !important;
    letter-spacing: 2px !important;
    margin: 12px 0 6px !important;
    padding-left: 10px !important;
    border-left: 2px solid #5a3c18 !important;
}

/* ── 选项按钮 ───────────────────────────────────────── */
.choice-btn > button {
    background: linear-gradient(180deg, #2c1e0c 0%, #1e1408 100%) !important;
    color: #d4b060 !important;
    border: 1px solid #4e3414 !important;
    border-bottom-width: 2px !important;
    border-radius: 2px !important;
    font-family: 'KaiTi', 'STKaiti', 'SimSun', serif !important;
    font-size: 0.93em !important;
    text-align: left !important;
    padding: 10px 16px !important;
    min-height: 54px !important;
    line-height: 1.55 !important;
    white-space: normal !important;
    word-break: break-all !important;
    transition: all 0.15s ease !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04) !important;
}
.choice-btn > button:hover {
    background: linear-gradient(180deg, #3a2a10 0%, #2c2010 100%) !important;
    color: #f0d060 !important;
    border-color: #8a6020 !important;
    transform: translateX(3px) !important;
    box-shadow: -3px 0 8px rgba(170,110,20,0.22) !important;
}

/* ── 自由输入框 ─────────────────────────────────────── */
.free-input textarea, .free-input input {
    background: #1a1208 !important;
    color: #d8c898 !important;
    border: 1px solid #4a3018 !important;
    border-radius: 2px !important;
    font-family: 'KaiTi', 'STKaiti', 'SimSun', serif !important;
    font-size: 0.95em !important;
}
.free-input textarea:focus, .free-input input:focus {
    border-color: #7a5020 !important;
    box-shadow: 0 0 6px rgba(180,120,40,0.2) !important;
}

/* ── 确认按钮 ───────────────────────────────────────── */
.submit-btn > button {
    background: linear-gradient(180deg, #5c3010 0%, #401e08 100%) !important;
    color: #f0d870 !important;
    border: 1px solid #7a4818 !important;
    border-radius: 2px !important;
    font-family: 'KaiTi', 'STKaiti', 'SimSun', serif !important;
    font-size: 0.95em !important;
}
.submit-btn > button:hover {
    background: linear-gradient(180deg, #6a3814 0%, #4c2610 100%) !important;
    box-shadow: 0 0 8px rgba(180,110,30,0.25) !important;
}

/* ── 新游戏按钮 ─────────────────────────────────────── */
.new-game-btn > button {
    background: linear-gradient(180deg, #6a3810 0%, #4a2408 100%) !important;
    color: #f5e080 !important;
    border: 1px solid #8a4e1a !important;
    border-radius: 2px !important;
    font-family: 'KaiTi', 'STKaiti', 'SimSun', serif !important;
    font-size: 1.02em !important;
    letter-spacing: 2px !important;
    padding: 10px !important;
    width: 100% !important;
}
.new-game-btn > button:hover {
    background: linear-gradient(180deg, #7a4818 0%, #5a2e10 100%) !important;
    box-shadow: 0 0 14px rgba(200,130,40,0.28) !important;
}

/* ── 状态面板 ───────────────────────────────────────── */
#status-panel {
    background: linear-gradient(180deg, #1a1008 0%, #120c06 100%);
    border: 1px solid #332210;
    border-left: 3px solid #6a4012;
    border-radius: 2px;
    padding: 18px 16px;
    min-height: 380px;
    box-shadow: inset 0 0 30px rgba(0,0,0,0.3);
}
#status-panel p, #status-panel li, #status-panel h3, #status-panel h4 {
    color: #c8b880 !important;
    font-family: 'SimSun', serif !important;
}
#status-panel strong { color: #e0c870 !important; }
#status-panel hr { border-color: #2e2010 !important; }
#status-panel code {
    background: rgba(80,60,20,0.3) !important;
    color: #d8b860 !important;
}
"""

# ── HTML 格式化工具 ────────────────────────────────────────────────────────────

def _format_turn(player_action: str, result: dict) -> str:
    html = ""
    if player_action:
        html += f'<div class="player-action">▶ {player_action}</div>'

    narration = result.get("narration", "").replace("\n", "<br>")
    html += f'<div class="narration-block">{narration}</div>'

    dlg = result.get("dialogue") or {}
    if dlg.get("text"):
        spk  = dlg.get("speaker", "")
        text = dlg["text"].replace("\n", "<br>")
        if spk:
            html += (
                f'<div class="dialogue-line">'
                f'<span class="speaker-name">【{spk}】</span>「{text}」'
                f'</div>'
            )
        else:
            html += f'<div class="dialogue-line">「{text}」</div>'

    frag = result.get("backstory_fragment", "")
    if frag:
        frag_html = frag.replace("\n", "<br>")
        html += (
            f'<div class="backstory-block">'
            f'<span style="color:#9878c8;font-size:0.8em;letter-spacing:4px;">'
            f'✦ 往事碎忆 ✦</span><br>{frag_html}'
            f'</div>'
        )

    if not result.get("consistency_passed", True):
        hint = result.get("repair_suggestion", "")
        if hint:
            html += f'<div class="repair-note">⚠ {hint}</div>'

    html += '<hr class="turn-divider">'
    return html


def _render_story(turns: list[str]) -> str:
    if turns:
        inner = "".join(turns)
        # 自动滚动到底部的 JS
        scroll_js = (
            '<script>'
            'setTimeout(()=>{'
            'const b=document.getElementById("story-box");'
            'if(b)b.scrollTop=b.scrollHeight;'
            '},80);'
            '</script>'
        )
        inner += scroll_js
    else:
        inner = (
            '<div class="empty-hint">'
            '崇祯十四年，天下大乱<br>'
            '点击「⚔ 开始新游戏」踏上旅途<br>'
            '<span style="font-size:0.7em;color:#3a2c10;letter-spacing:1px;">StoryWeaver · AI 文字冒险</span>'
            '</div>'
        )
    return f'<div id="story-box">{inner}</div>'


def _format_status(state) -> str:
    if state is None:
        return "未开始游戏"

    relation  = state.get("companion_relation", 0)
    rep       = state.get("reputation",  0)
    silver    = state.get("silver",      0)
    inventory = state.get("inventory",   [])
    location  = state.get("player_location", "")
    backstory = state.get("revealed_backstory", [])
    flags     = state.get("plot_flags",  {})
    turn_id   = state.get("turn_id",     0)
    act       = state.get("current_act", 1)

    filled   = int(relation / 10)
    bar      = "🟥" * filled + "⬛" * (10 - filled)
    rep_text = f"+{rep}" if rep > 0 else str(rep)
    act_names = {1: "华州", 2: "阌乡", 3: "崤山", 4: "洛阳"}

    lines = [
        f"### 📍 {location}",
        f"*第 {act} 幕 · {act_names.get(act,'?')} · 第 {turn_id} 回合*",
        "---",
        f"**穗的信任度**",
        f"{bar}  `{relation}/100`",
        "",
        f"**名声** `{rep_text}`　　**铜钱** `{silver} 文`",
        "",
        f"**背包**",
    ]

    if inventory:
        for item in inventory:
            lines.append(f"- {item}")
    else:
        lines.append("- *空*")

    if backstory:
        lines += ["---", f"**📖 已知线索** *({len(backstory)} 条)*"]
        for b in backstory[-3:]:
            snippet = b[:24] + "…" if len(b) > 24 else b
            lines.append(f"- {snippet}")

    flag_labels = {
        "saved_refugee":   "✅ 救助过难民",
        "betrayed_trust":  "❌ 曾欺骗穗",
        "joined_rebels":   "✅ 与义军合作",
        "revealed_secret": "✅ 揭露委托真相",
        "sacrificed_self": "✅ 挺身而出",
        "knows_pig_demon": "⚠️ 知晓豚妖",
    }
    active = [flag_labels[k] for k in flag_labels if flags.get(k)]
    if active:
        lines += ["---", "**⚑ 命运选择**"]
        lines += active

    return "\n".join(lines)


def _update_buttons(choices: list[str]):
    updates = []
    for i in range(4):
        if i < len(choices):
            updates.append(gr.update(value=choices[i], visible=True))
        else:
            updates.append(gr.update(value="", visible=False))
    return updates


# ── 事件处理 ──────────────────────────────────────────────────────────────────

def handle_new_game():
    global _story_turns
    _story_turns = []
    result = session.new_game()

    act_title = '<div class="act-title">═══ 第一幕 · 华州 ═══</div>'
    _story_turns.append(act_title)
    _story_turns.append(_format_turn("", result))

    story_html  = _render_story(_story_turns)
    status_md   = _format_status(session.get_state())
    btn_updates = _update_buttons(result.get("next_choices", []))
    return [story_html, status_md] + btn_updates + [""]


def handle_choice(choice_text: str):
    global _story_turns
    if not choice_text or session.get_state() is None:
        return [gr.update()] * 7

    result = session.step(choice_text)
    state  = session.get_state()

    if state and result.get("state_delta", {}).get("new_location"):
        act    = state.get("current_act", 1)
        titles = {1: "华州", 2: "阌乡", 3: "崤山", 4: "洛阳"}
        act_title = f'<div class="act-title">═══ 第{act}幕 · {titles.get(act,"")} ═══</div>'
        _story_turns.append(act_title)

    _story_turns.append(_format_turn(choice_text, result))

    story_html  = _render_story(_story_turns)
    status_md   = _format_status(state)
    btn_updates = _update_buttons(result.get("next_choices", []))
    return [story_html, status_md] + btn_updates + [""]


def handle_free_input(text: str):
    if not text.strip():
        return [gr.update()] * 7
    return handle_choice(text.strip())


# ── 构建 Gradio 应用 ──────────────────────────────────────────────────────────

with gr.Blocks(title="StoryWeaver · 明末千里行") as demo:

    # ── 标题 ────────────────────────────────────────────────────────────────
    gr.HTML("""
    <div id="app-header">
      <h1>饿殍 · 明末千里行</h1>
      <p>StoryWeaver &nbsp;·&nbsp; LangGraph 多 Agent AI 文字冒险 &nbsp;·&nbsp; COMP5423 NLP Project</p>
    </div>
    """)

    with gr.Row(equal_height=False):

        # ── 左：故事区 ────────────────────────────────────────────────────
        with gr.Column(scale=3, min_width=500):
            story_display = gr.HTML(value=_render_story([]))

            # 选项按钮
            gr.HTML('<div class="choice-label">选择你的行动：</div>')
            with gr.Row():
                btn1 = gr.Button("—", elem_classes=["choice-btn"], visible=False)
                btn2 = gr.Button("—", elem_classes=["choice-btn"], visible=False)
            with gr.Row():
                btn3 = gr.Button("—", elem_classes=["choice-btn"], visible=False)
                btn4 = gr.Button("—", elem_classes=["choice-btn"], visible=False)

            gr.HTML('<div class="choice-label" style="margin-top:14px;">自由行动：</div>')
            with gr.Row():
                free_input = gr.Textbox(
                    placeholder="输入你的行动……",
                    show_label=False,
                    scale=5,
                    elem_classes=["free-input"],
                    lines=1,
                )
                submit_btn = gr.Button("确认", scale=1, elem_classes=["submit-btn"])

        # ── 右：状态面板 ──────────────────────────────────────────────────
        with gr.Column(scale=1, min_width=220):
            new_game_btn = gr.Button("⚔ 开始新游戏", elem_classes=["new-game-btn"])
            gr.HTML('<hr style="border-color:#3a2510; margin:12px 0 8px;">')
            with gr.Group(elem_id="status-panel"):
                status_display = gr.Markdown("*准备开始旅途……*")

    # ── 事件绑定 ──────────────────────────────────────────────────────────
    _outputs = [story_display, status_display, btn1, btn2, btn3, btn4, free_input]

    new_game_btn.click(fn=handle_new_game, outputs=_outputs)

    for btn in [btn1, btn2, btn3, btn4]:
        btn.click(fn=handle_choice, inputs=[btn], outputs=_outputs)

    submit_btn.click(fn=handle_free_input, inputs=[free_input], outputs=_outputs)
    free_input.submit(fn=handle_free_input, inputs=[free_input], outputs=_outputs)


if __name__ == "__main__":
    demo.launch(
        server_port=7860,
        share=False,
        css=CUSTOM_CSS,
        theme=gr.themes.Base(
            primary_hue="orange",
            neutral_hue="stone",
        ),
    )
