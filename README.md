---
title: StoryWeaver 饿殍·明末千里行
emoji: ⚔️
colorFrom: yellow
colorTo: red
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
python_version: "3.11"
---

# 📜 StoryWeaver — AI-Powered Text Adventure Game

> **COMP5423 Natural Language Processing · Group Project · PolyU 2026**
>
> 《饿殍：明末千里行》原创角色 × LangGraph 多 Agent 叙事引擎

[![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green)](https://github.com/langchain-ai/langgraph)
[![Gradio](https://img.shields.io/badge/UI-Gradio-orange?logo=gradio)](https://gradio.app)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek--Chat-purple)](https://deepseek.com)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

---

## ✨ 项目简介

StoryWeaver 是一个基于 **LangGraph 多智能体状态机** 构建的明末题材文字冒险游戏引擎。玩家扮演主角「良」，带着哑女同伴「穗」沿 **华州 → 阌乡 → 崤山 → 洛阳** 四幕路线行进，系统实时生成沉浸式叙事，同时维护自洽的世界状态。

**核心 NLP 能力：**

| 模块 | 方法 | 指标 |
|------|------|------|
| 意图识别 (NLU) | 长度加权关键词 + LLM Fallback | **100%** (20/20) |
| 一致性检测 | 5条硬规则 + DeepSeek深层检查 | **100%** (8/8) |
| 上下文叙事生成 (NLG) | DeepSeek · system prompt 世界观注入 | LLM-judge ≥ 3.5/5 |
| 选项差异度 | BLEU 逆相似度 | **0.986** (目标 ≥ 0.4) |

---

## 🏗️ 系统架构

```
玩家输入
    │
    ▼
┌─────────────────┐   规则层(100%) + LLM fallback
│  IntentAgent    │──────────────────────────────►  intent · entities
└────────┬────────┘
         │
         ▼
┌─────────────────┐   5 硬规则 + LLM 深层检查
│ConsistencyAgent │─────────────────────────────►  passed / violation
└──────┬──────────┘
    FAIL│    PASS│
       ▼         ▼
┌──────────┐  ┌─────────────────┐
│  Repair  │─►│  NarratorAgent  │  DeepSeek · max_tokens=900
│  Agent   │  │  旁白+对话+暗线 │
└──────────┘  └────────┬────────┘
                        │  state_delta
                        ▼
               ┌─────────────────┐
               │   WorldAgent    │  纯规则 · 无 LLM
               │  状态同步更新   │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │   ChoiceAgent   │  DeepSeek · temp=1.0
               │  3-4个差异选项  │
               └────────┬────────┘
                        │
                        ▼
                  Gradio UI 输出
```

> 详细架构图：打开 [`architecture.html`](architecture.html)（浏览器直接查看）

---

## 🚀 快速开始

### 环境要求

- Python **3.10+**（推荐 3.14，项目开发环境）
- DeepSeek API Key（在 [platform.deepseek.com](https://platform.deepseek.com) 申请）

### 1. 克隆项目

```bash
git clone https://github.com/<your-org>/StoryWeaver.git
cd StoryWeaver
```

### 2. 创建虚拟环境 & 安装依赖

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，将 your_deepseek_api_key_here 替换为你的真实 Key
```

`.env` 内容示例：
```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

### 4. 启动游戏 UI

```bash
python ui/app.py
# 浏览器访问 http://127.0.0.1:7860
```

### 5. 运行评估

```bash
python evaluation/run_eval.py
# 结果输出至 logs/eval_result.csv 和 logs/eval_summary.json
```

---

## ☁️ Vercel 部署

项目已配置好 Vercel 部署支持，使用 Python Serverless Functions 作为后端 API，静态 HTML 作为前端。

### 部署步骤

1. **安装 Vercel CLI**

```bash
npm i -g vercel
```

2. **登录 Vercel**

```bash
vercel login
```

3. **配置环境变量**

在 [Vercel 控制台](https://vercel.com) 项目设置中添加以下环境变量：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥（**必填**） | `sk-xxxxxxxxxxxx` |
| `DEEPSEEK_BASE_URL` | API 端点（可选） | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名称（可选） | `deepseek-chat` |

也可通过 CLI 添加：
```bash
vercel env add DEEPSEEK_API_KEY
```

4. **部署**

```bash
# 预览部署
vercel

# 生产部署
vercel --prod
```

### 架构说明

| 组件 | 说明 |
|------|------|
| `vercel.json` | Vercel 部署配置（路由、函数超时等） |
| `api/new_game.py` | Serverless Function — 初始化新游戏 |
| `api/step.py` | Serverless Function — 处理每回合玩家输入 |
| `public/index.html` | 静态前端（明末卷轴风 UI） |

> ⚠️ **注意事项：**
> - Vercel Free 计划 Serverless Function 最大执行时间为 10 秒，DeepSeek API 调用可能超时。建议使用 **Pro 计划**（60 秒超时）。
> - 游戏状态存储在客户端浏览器中，刷新页面会丢失进度。
> - 环境变量 `DEEPSEEK_API_KEY` 必须在 Vercel 项目设置中配置，切勿提交到代码仓库。

---

## 📁 项目结构

```
StoryWeaver/
├── storyweaver/               # 核心引擎
│   ├── agents/
│   │   ├── intent_agent.py        # NLU：意图识别 + 实体抽取
│   │   ├── consistency_agent.py   # 一致性守卫（5规则 + LLM）
│   │   ├── repair_agent.py        # 叙事化修复
│   │   ├── narrator_agent.py      # 核心叙事 NLG
│   │   ├── world_agent.py         # 世界状态同步（纯规则）
│   │   └── choice_agent.py        # 差异化选项生成
│   ├── graph.py               # LangGraph StateGraph 定义
│   ├── game_session.py        # 公共接口：new_game() / step()
│   ├── schemas.py             # GameState TypedDict
│   └── config.py              # DeepSeek client + 超参数
│
├── prompts/                   # 所有 Prompt 模板
│   ├── world_setting.py           # 世界观 System Prompt
│   ├── narrator_prompts.py        # 叙事生成 prompt builder
│   ├── intent_prompts.py          # 意图分类 prompt
│   ├── consistency_prompts.py     # 一致性检查 + 修复 prompts
│   └── choice_prompts.py          # 选项生成 prompt
│
├── data/
│   ├── scenarios/
│   │   └── act1_huazhou.json      # 第一幕：华州开局场景
│   ├── test_cases/
│   │   └── eval_inputs.json       # 20 意图 + 8 一致性 + 8 流程测试
│   └── world/
│       ├── npcs.json              # NPC 数据
│       ├── locations.json         # 地点数据
│       └── items.json             # 道具数据
│
├── evaluation/
│   ├── metrics.py             # 5 大评估指标（coherence/diversity/accuracy...）
│   └── run_eval.py            # 批量评估 CLI
│
├── ui/
│   └── app.py                 # Gradio 双栏 UI（port 7860）
│
├── docs/
│   └── TECHNICAL_SPEC.md      # 大厂级技术规格说明书
│
├── api/                       # Vercel Serverless Functions
│   ├── new_game.py                # 新游戏 API
│   └── step.py                    # 游戏回合 API
│
├── public/                    # Vercel 静态前端
│   └── index.html                 # 游戏 UI（明末卷轴风）
│
├── architecture.html          # 可视化架构图（浏览器打开）
├── vercel.json                # Vercel 部署配置
├── requirements.txt
├── .env.example               # API Key 配置模板
└── README.md
```

---

## 🎮 游戏设定

| 要素 | 说明 |
|------|------|
| **时代背景** | 明末崇祯年间，饥荒与流民 |
| **主角** | 良 —— 接受护送委托的旅人 |
| **同伴** | 穗 —— 哑女，用布条写字交流，信任度 0-100 |
| **向导** | 舌头 —— 熟悉路况的 NPC |
| **路线** | 华州 → 阌乡 → 崤山 → 洛阳（4幕） |
| **隐藏要素** | 豚妖、委托书秘密、暗线碎片 |

**世界状态变量：**

```python
companion_relation: int   # 穗的信任度 [0, 100]，影响结局分支
reputation:        int   # 声誉 [-50, 50]，影响 NPC 态度
silver:            int   # 铜钱，用于贿赂/购买
plot_flags:        dict  # 情节解锁标记（knows_pig_demon 等）
```

---

## 📊 评估结果

运行 `python evaluation/run_eval.py` 复现以下指标：

| 指标 | 本系统 | 课程阈值 |
|------|--------|---------|
| 意图识别准确率 | **100%** (20/20) | ≥ 85% |
| 一致性检测准确率 | **100%** (8/8) | ≥ 80% |
| 选项差异度 (1−BLEU) | **0.986** | ≥ 0.4 |
| 叙事连贯性 (LLM-as-judge) | **3.5–5.0 / 5** | ≥ 3.5 |
| 响应延迟 P50 | ~15,700 ms | < 5,000 ms ⚠️ |

> ⚠️ **延迟说明**：P50 ~15.7s 由 DeepSeek API 网络延迟主导（NarratorAgent 单次调用 max_tokens=900），非本地计算瓶颈。建议 Demo 时开启流式输出或预先缓存。

---

## ⚙️ 关键配置

`storyweaver/config.py` 中的超参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `GENERATION_TEMPERATURE` | 0.8 | NarratorAgent 创意度 |
| `INTENT_TEMPERATURE` | 0.1 | IntentAgent LLM 层（低随机性） |
| `CONSISTENCY_TEMPERATURE` | 0.2 | ConsistencyAgent LLM 层 |
| `CHOICE_TEMPERATURE` | 0.9 | ChoiceAgent 多样性 |
| `MAX_HISTORY_TURNS` | 8 | turn_history 滑动窗口 |
| `CONTEXT_TURNS` | 3 | NarratorAgent 历史上下文窗口 |

---

## 🛠️ 开发指南

### 新增场景

1. 在 `data/scenarios/` 创建 `act2_wanxiang.json`（参考 `act1_huazhou.json` 格式）
2. 在 `storyweaver/agents/world_agent.py` 的 `LOCATION_ACT` 字典中补充地点映射

### 新增意图类别

1. 在 `storyweaver/agents/intent_agent.py` 的 `INTENT_KEYWORDS` 中添加新意图及关键词
2. 在 `data/test_cases/eval_inputs.json` 中添加对应测试样本
3. 运行 `python evaluation/run_eval.py` 验证准确率

### 调试单个 Agent

```python
# 直接测试 IntentAgent
from storyweaver.agents.intent_agent import run_intent_agent
result = run_intent_agent({"player_input": "把干粮分给月儿", "agent_logs": []})
print(result)  # {'intent': 'HELP', 'entities': {}, 'intent_confidence': 0.79, ...}
```

### 常见问题

| 问题 | 解决方案 |
|------|----------|
| `UnicodeEncodeError` (Windows) | 在脚本顶部添加 `import io, sys; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` |
| `Pydantic V1 deprecation warning` | 来自 langchain-core，非致命，可忽略 |
| API 超时 / 连接失败 | 检查 `.env` 中的 Key 是否正确；检查网络能否访问 `api.deepseek.com` |
| `FileNotFoundError: Scenario not found` | 请从**项目根目录**运行，而非子目录 |

---

## 📅 重要截止日期

| 事项 | 日期 |
|------|------|
| PPT 提交（Blackboard） | **2026-04-07 23:59** |
| 课堂展示 + Live Demo | **2026-04-08 18:30–21:20** |
| 最终报告提交（PDF） | **2026-04-26 23:59** |

---

## 👥 团队成员

> 请各成员在此处填写自己的信息

| 姓名 | 学号 | 分工 |
|------|------|------|
| _(待填写)_ | _(待填写)_ | _(待填写)_ |
| _(待填写)_ | _(待填写)_ | _(待填写)_ |
| _(待填写)_ | _(待填写)_ | _(待填写)_ |

---

## 📄 License

[MIT License](LICENSE) — 仅供课程学习使用，请勿商用。

---

<p align="center">
  <sub>COMP5423 · The Hong Kong Polytechnic University · 2026</sub>
</p>
