# SNhelper

一个面向长期使用的“个人认知外骨骼”最小实现：一个透明的总调度器，配合四个职责清晰的 Agent。

## 结构

- `Router`：将碎碎念、知识碎片、目标、复盘和社交问题路由到一个或多个 Agent。
- `Archivist`：提取标题和标签，将思维碎片持久化；默认使用 SQLite，接口可替换成 Chroma、Qdrant 或 LangChain Retriever。
- `Enforcer`：把宏大目标压缩成有完成标志的物理动作和 10 分钟实验。
- `Strategist`：结合近期记忆生成复盘问题、长期决策规则和下一次实验。
- `Simulator`：生成对方可能目标、开场话术、被质疑/拒绝/冲突升级时的应急卡片。

## 快速开始

```powershell
cd C:\Git\SNhelper\SNhelper
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m snhelper ask "我想记录一个关于个人创业的灵感，并拆解第一步"
python -m snhelper search "创业"
python -m pytest -q
```

启动 FastAPI 后端和 Web 控制面板：

```powershell
pip install -e ".[web,dev]"
$env:SNHELPER_API_KEY = "local-dev-key"  # 可选
uvicorn snhelper.web_api:app --reload --host 127.0.0.1 --port 8000

cd web
npm install
npm run dev
```

打开 `http://localhost:5173`，在“系统设置”中选择 `FastAPI REST` 或 `FastAPI SSE`。`FastAPI 地址`填写 `http://127.0.0.1:8000`，外部供应商的 OpenAI 兼容地址和 Key 填在“外部模型服务”（例如 `https://api.openai.com/v1`、模型 `gpt-4o-mini`），点击“测试模型连接”。后端 API 也可以通过 `SNHELPER_DB_PATH` 指向独立 SQLite 文件。

默认模式不需要 API Key，可直接运行。要接入 LangChain 的 ChatOpenAI：

```powershell
pip install -e ".[langchain]"
$env:OPENAI_API_KEY = "..."
python -m snhelper ask --llm "帮我复盘最近的创业方向"
```

`Orchestrator` 接收任意文本并返回结构化的 `OrchestrationResult`。可以在上层接入 FastAPI、Telegram、桌面客户端或定时任务；持久化和 Agent 接口不需要改动。
