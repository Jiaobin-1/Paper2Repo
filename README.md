# Paper2Repo

Paper2Repo 是一个面向 AI 论文阅读与复现规划的本地 MVP。用户上传论文 PDF 后，后端会解析论文、切分 chunk、运行 LangGraph 占位 workflow，并生成结构化分析结果和 Markdown 复现规划报告。

第一版目标是把“读懂论文 -> 复现论文”的工程骨架跑通，不做联网搜索、不做复杂向量检索、不自动生成完整复现代码仓库。

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

DATABASE_URL=sqlite:///./data/paper2repo.db
UPLOAD_DIR=./storage/uploads
REPORT_DIR=./storage/reports
```

当前 MVP 不会主动调用复杂 LLM prompt，但已经预留 OpenAI-compatible 配置入口。

## API

- `GET /health`
- `POST /api/papers/upload`
- `GET /api/papers`
- `GET /api/papers/{paper_id}`
- `POST /api/papers/{paper_id}/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/analysis`
- `GET /api/runs/{run_id}/report`

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

## Frontend Quick Start

```bash
cd frontend
npm install
npm run dev
```

默认后端地址是 `http://localhost:8000`。如需修改，设置：

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
- Markdown 报告生成
- Next.js 最小页面骨架

后续重点：

- 写正式 LLM prompt
- 提升元信息、方法、实验抽取质量
- 完善前端结果展示
- 增加示例论文和测试用例
