# Paper2Repo

Paper2Repo 是一个面向 AI 论文阅读与复现规划的本地 MVP。用户上传论文 PDF 后，系统会解析论文、切分 chunk、运行 LangGraph workflow，并生成结构化论文理解结果和 Markdown 复现规划报告。

第一版目标是把“读懂论文 -> 复现论文”的本地工作流跑通，不做联网搜索、不做复杂向量检索、不自动生成完整复现代码仓库。

## Tech Stack

- Backend: FastAPI
- Frontend: Next.js
- Agent orchestration: LangGraph
- Database: SQLite
- PDF parser: PyMuPDF
- Structured output: Pydantic
- LLM API: OpenAI-compatible API from environment variables
- Retrieval: section title + keyword retrieval

## Backend Quick Start

本机默认使用 `agent-learning` conda 环境测试后端：

```bash
conda run -n agent-learning python -m pip install -r backend/requirements.txt
cd backend
conda run -n agent-learning python -m uvicorn app.main:app --reload
```

检查服务：

```bash
curl http://127.0.0.1:8000/health
```

## Environment

复制 `.env.example` 为 `.env`，按需填写：

```bash
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_MODEL_OPTIONS=gpt-4o-mini,gpt-4o,deepseek-chat

DATABASE_URL=sqlite:///./data/paper2repo.db
UPLOAD_DIR=./storage/uploads
REPORT_DIR=./storage/reports
```

当前 MVP 已接入 OpenAI-compatible 结构化输出入口。配置 `OPENAI_API_KEY` 后，核心分析节点会优先调用 LLM 生成符合 Pydantic schema 的 JSON；未配置时会使用基于检索片段的本地 fallback，保证流程仍可跑通。

### 接入自己的 OpenAI-compatible LLM

在项目根目录创建 `.env`，不要放到 `backend/` 里面：

```bash
cp .env.example .env
```

填写你的服务商配置：

```bash
OPENAI_API_KEY=你的 API Key
OPENAI_BASE_URL=https://你的服务商地址/v1
OPENAI_MODEL=你的模型名
OPENAI_MODEL_OPTIONS=模型名1,模型名2,模型名3
```

示例：

```bash
# Example only. Use the exact base URL and model name from your provider.
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.example.com/v1
OPENAI_MODEL=deepseek-chat
OPENAI_MODEL_OPTIONS=deepseek-chat,deepseek-reasoner
```

修改 `.env` 后需要重启后端，因为配置会在应用启动时读取：

```bash
cd backend
conda run -n agent-learning python -m uvicorn app.main:app --reload
```

如果你的服务商兼容 OpenAI Chat Completions，Paper2Repo 会通过 `OPENAI_BASE_URL`、`OPENAI_API_KEY` 和当前默认模型调用它。`OPENAI_MODEL` 是首次默认模型，`OPENAI_MODEL_OPTIONS` 是前端下拉框可选模型列表；如果不配置 `OPENAI_MODEL_OPTIONS`，前端只会显示 `OPENAI_MODEL`。

前端会读取后端的 `GET /api/llm/config`，显示：

```text
LLM 是否已配置
当前 base_url
当前默认模型
可选模型列表
```

在前端切换模型后，后端会保存为全局默认模型，后续新启动的 run 会使用该模型；已经运行中的 run 不受影响。每个 run 的实际模型会通过 `GET /api/runs/{run_id}` 的 `model_name` 字段返回。

## API

- `GET /health`
- `POST /api/papers/upload`
- `GET /api/papers`
- `GET /api/papers/{paper_id}`
- `POST /api/papers/{paper_id}/runs`
- `GET /api/llm/config`
- `PUT /api/llm/config`
- `GET /api/runs/{run_id}`
- `GET /api/runs`
- `GET /api/runs/{run_id}/analysis`
- `GET /api/runs/{run_id}/report`
- `GET /api/runs/{run_id}/report.md`
- `GET /api/runs/{run_id}/report.pdf`

## Workflow

```text
parse_pdf_node
-> chunk_paper_node
-> extract_metadata_node
-> classify_paper_type_node
-> understand_paper_node
-> analyze_method_node
-> analyze_experiments_node
-> plan_reproduction_node
-> generate_report_node
-> persist_result_node
```

`retrieve_context` 是工具函数，不进入主流程。第一版只做章节标题和关键词检索。

## Local Demo Flow

1. 启动后端：

```bash
cd backend
conda run -n agent-learning python -m uvicorn app.main:app --reload
```

2. 启动前端：

```bash
cd frontend
npm install
npm run dev
```

3. 打开 `http://localhost:3000`，按页面流程操作：

```text
上传 PDF
-> 看到 paper_id
-> 选择分析模型
-> 点击启动分析
-> 立即看到 run_id
-> 前端轮询 run 状态并展示 workflow 进度
-> completed 后自动展示 Markdown 报告
-> 进入报告详情页，下载 Markdown 或 PDF
```

## Frontend Quick Start

```bash
cd frontend
npm install
npm run dev
```

前端默认通过 Next.js rewrite 把 `/api/*` 转发到 `http://127.0.0.1:8000`。如需改为直接访问其他后端地址，设置：

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Current MVP Status

已完成：

- FastAPI 最小后端
- SQLite 初始化
- PDF 上传保存
- PyMuPDF 解析入口
- LangGraph workflow 骨架
- Pydantic schema
- section title + keyword retrieval 工具
- OpenAI-compatible 结构化输出入口
- Markdown 报告生成
- PDF 报告下载
- Markdown 报告下载
- 最近分析列表和 Run 报告详情页
- Next.js 最小演示闭环
- 后台分析任务与前端轮询进度
- 前端模型选择与后端全局默认模型配置

后续重点：

- 提升元信息、方法、实验抽取质量
- 增加历史论文列表和报告详情页
- 增加示例论文和测试用例

## Example Report

示例报告见：

```text
docs/examples/sample_report.md
```
