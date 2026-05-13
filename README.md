# Paper2Repo

[![CI](https://github.com/YOUR_USERNAME/Paper2Repo/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/Paper2Repo/actions/workflows/ci.yml)

Paper2Repo 是一个面向 AI 论文阅读与复现规划的本地工具。用户上传论文 PDF 后，系统会解析论文、运行 10 节点 LangGraph 分析流水线，生成结构化论文理解结果和 Markdown/PDF 复现规划报告，并支持基于论文内容的追问对话、代码骨架生成、论文知识库语义搜索等高级功能。

## 核心功能

- **PDF 上传与解析**：拖拽上传，PyMuPDF 提取文本，自动检测章节结构
- **arXiv 导入**：输入 arXiv ID 或 URL，自动下载 PDF 并启动分析
- **10 节点分析流水线**：元信息提取 → 论文分类 → 方法拆解 → 实验分析 → 复现规划 → 报告生成
- **结构化复现报告**：中英双语 Markdown/PDF 报告，含方法模块、实验矩阵、风险点、检查清单
- **追问对话 (Q&A)**：报告生成后可就论文提问，支持 SSE 流式输出，超长对话自动摘要
- **代码骨架生成**：基于复现计划自动生成项目骨架 zip，含目录结构、代码模板、README、PLAN.md
- **论文知识库**：所有已分析论文自动建立向量索引，支持跨论文语义搜索
- **多论文比较**：选择 2-4 篇已完成报告进行结构化对比
- **Papers With Code**：基于分析结果推荐相关论文和代码资源链接
- **向量检索**：sentence-transformers 嵌入检索，60% 语义 + 40% 关键词混合打分
- **双语支持**：界面语言和报告语言独立配置（中文/英文）
- **响应式设计**：移动端适配，报告全屏查看
- **节点级容错**：分析节点失败不中断流程，失败节点写入报告附录

## Tech Stack

| 层级 | 技术 |
|------|------|
| Backend | FastAPI + Pydantic v2 |
| Agent | LangGraph (10-node StateGraph) |
| Database | SQLite (WAL mode) |
| PDF | PyMuPDF |
| LLM | OpenAI-compatible API (可选) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Frontend | Next.js 16 + React 19 + TypeScript |
| Testing | pytest (162) + vitest (26) + Playwright (20) |
| Linting | ruff + mypy + tsc |

## Quick Start

### 1. 环境配置

```bash
cp .env.example .env
# 编辑 .env，填写 OPENAI_API_KEY（可选，不填则使用本地 fallback）
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
# Health check: curl http://127.0.0.1:8000/health
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 4. 使用

打开 `http://localhost:3000`，按页面流程操作：

```
上传 PDF / arXiv 导入 → 选择模型 → 启动分析 → 查看进度 → 查看报告
→ 追问对话 / 下载代码骨架 / 搜索知识库 / 比较多篇论文
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | LLM API Key（可选） | 空（使用 fallback） |
| `OPENAI_BASE_URL` | API 地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 默认模型 | `gpt-4o-mini` |
| `OPENAI_MODEL_OPTIONS` | 前端可选模型列表 | `gpt-4o-mini,gpt-4o` |
| `DATABASE_URL` | SQLite 路径 | `sqlite:///./data/paper2repo.db` |
| `UPLOAD_DIR` | 上传目录 | `./storage/uploads` |
| `REPORT_DIR` | 报告目录 | `./storage/reports` |
| `UPLOAD_MAX_MB` | 上传大小限制 | `50` |
| `RUN_STALE_AFTER_MINUTES` | 任务超时（分钟） | `60` |

## API

完整 API 文档启动后访问 `http://127.0.0.1:8000/docs`（Swagger UI）。

主要端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/papers/upload` | 上传 PDF |
| `POST` | `/api/papers/{paper_id}/runs` | 启动分析 |
| `GET` | `/api/runs/{run_id}` | 查询任务状态 |
| `GET` | `/api/runs/{run_id}/report` | 获取报告 |
| `GET` | `/api/runs/{run_id}/report.md` | 下载 Markdown |
| `GET` | `/api/runs/{run_id}/report.pdf` | 下载 PDF |
| `GET` | `/api/runs/{run_id}/skeleton` | 下载代码骨架 zip |
| `POST` | `/api/runs/{run_id}/qa` | 追问对话 |
| `POST` | `/api/runs/{run_id}/qa/stream` | 追问对话 (SSE 流式) |
| `GET` | `/api/runs/{run_id}/qa` | 对话历史 |
| `GET` | `/api/runs/{run_id}/pwc-links` | Papers With Code 推荐 |
| `POST` | `/api/arxiv/import` | arXiv 论文导入 |
| `GET` | `/api/arxiv/{id}/versions` | arXiv 版本列表 |
| `GET` | `/api/compare` | 多论文比较 |
| `GET` | `/api/compare/available` | 可比较任务列表 |
| `GET` | `/api/knowledge/search` | 知识库语义搜索 |
| `GET` | `/api/knowledge/papers` | 知识库已索引论文 |
| `GET/PUT` | `/api/settings` | 系统设置 |

## 分析流水线

```
parse_pdf → chunk_paper → extract_metadata → classify_paper_type
→ understand_paper → analyze_method → analyze_experiments
→ plan_reproduction → generate_report → persist_result
```

- **关键节点**（parse_pdf, chunk_paper）：失败时中断流程
- **分析节点**（understand ~ plan）：失败时跳过，后续继续
- **报告生成**：即使部分失败，仍生成部分报告 + 错误附录
- **向量索引**：`persist_result` 完成后自动将 chunk 嵌入写入 `paper_embeddings` 表

## 页面路由

| 路径 | 说明 |
|------|------|
| `/` | 首页：上传、运行历史、工作流 |
| `/arxiv` | arXiv 论文导入 |
| `/knowledge` | 论文知识库语义搜索 |
| `/compare` | 多论文比较 |
| `/settings` | 设置（语言、模型） |
| `/runs/[runId]` | 报告详情 + Q&A + 代码骨架下载 |
| `/papers/[paperId]` | 论文详情 + 运行列表 |

## 开发

### 后端测试

```bash
cd backend
pip install -r requirements-dev.txt

# 全部测试 (162 tests)
python -m pytest tests/ -v

# Lint
python -m ruff check app/ tests/

# Type check
python -m mypy app/ --ignore-missing-imports
```

### 前端测试

```bash
cd frontend

# Type check
npm run lint

# 单元测试 (26 tests, vitest)
npm run test:unit

# E2E 测试 (20 tests, Playwright)
npx playwright install chromium
npx playwright test
```

### CI

推送到 `main` 分支或创建 PR 时，GitHub Actions 自动运行：
- 后端：ruff + mypy + pytest
- 前端：tsc + vitest + playwright

## 项目结构

```
Paper2Repo/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph 流水线
│   │   │   ├── nodes/       # 10 个分析节点
│   │   │   ├── graph.py     # 流水线编排
│   │   │   ├── state.py     # TypedDict 状态
│   │   │   └── prompts.py   # LLM 提示词
│   │   ├── api/             # FastAPI 路由
│   │   │   ├── routes_papers.py    # 论文上传
│   │   │   ├── routes_runs.py      # 运行管理 + 报告 + 代码骨架
│   │   │   ├── routes_qa.py        # Q&A 对话 (流式)
│   │   │   ├── routes_arxiv.py     # arXiv 导入
│   │   │   ├── routes_compare.py   # 多论文比较
│   │   │   ├── routes_knowledge.py # 知识库搜索
│   │   │   ├── routes_pwc.py       # Papers With Code
│   │   │   ├── routes_llm.py       # LLM 配置
│   │   │   └── routes_settings.py  # 系统设置
│   │   ├── core/            # 配置、数据库
│   │   ├── schemas/         # Pydantic 模型
│   │   └── services/        # 业务逻辑
│   │       ├── code_skeleton.py    # 代码骨架生成
│   │       ├── arxiv_client.py     # arXiv API 客户端
│   │       ├── qa_service.py       # Q&A 服务 (含对话摘要)
│   │       ├── retrieval.py        # 检索 + 向量索引
│   │       └── ...
│   ├── tests/               # 162 个测试
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── components/
│   │   │   ├── upload/      # PDF 上传组件
│   │   │   ├── report/      # 报告、Q&A、代码骨架、PwC
│   │   │   ├── history/     # 运行历史
│   │   │   ├── knowledge/   # 知识库搜索
│   │   │   └── shared/      # 共享组件
│   │   ├── arxiv/           # arXiv 导入页
│   │   ├── knowledge/       # 知识库页
│   │   ├── compare/         # 多论文比较页
│   │   ├── papers/          # 论文详情页
│   │   ├── runs/            # 报告详情页
│   │   └── settings/        # 设置页
│   ├── lib/                 # 工具函数、API 客户端
│   ├── e2e/                 # Playwright E2E 测试
│   └── package.json
├── .github/workflows/ci.yml # CI 配置
├── CLAUDE.md                # Claude Code 指南
└── README.md
```

## 许可证

MIT
