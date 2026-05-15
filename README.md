# Paper2Repo

Paper2Repo is a local AI-paper analysis and reproduction-planning tool. It ingests paper PDFs or arXiv IDs, runs an 11-node LangGraph analysis workflow, and produces structured reports, Q&A, citations, knowledge search, comparison views, and exportable reproduction artifacts.

The app works without an API key by using deterministic local fallback analysis. If `OPENAI_API_KEY` is configured, analysis and Q&A use an OpenAI-compatible chat API.

## Features

- PDF upload, validation, parsing, section detection, and text chunking.
- arXiv import, arXiv version lookup, and version-comparison workflow.
- 11-node analysis pipeline: parse, chunk, citation extraction, metadata extraction, paper classification, understanding, method analysis, experiment analysis, reproduction planning, report generation, persistence.
- Structured Markdown report with evidence references, missing-item audit, understand-to-reproduce roadmap, method modules, experiment matrix, risks, acceptance criteria, and code skeleton plan.
- Report downloads as Markdown, PDF, HTML, and LaTeX.
- Q&A over completed reports, including SSE streaming.
- Code skeleton zip generation from the reproduction plan.
- Knowledge-base search over analyzed paper chunks with hybrid semantic/keyword retrieval.
- Batch upload and batch analysis status.
- Multi-paper comparison and citation-network view.
- Bilingual UI/report settings and responsive frontend.
- Recoverable background jobs with node-level fault tolerance for non-critical analysis nodes.

## Tech Stack

| Layer | Tech |
| --- | --- |
| Backend | FastAPI, Pydantic v2 |
| Agent workflow | LangGraph `StateGraph` |
| Database | SQLite with WAL mode |
| PDF parsing | PyMuPDF |
| LLM | OpenAI-compatible chat API, optional |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` |
| Frontend | Next.js 16, React 19, TypeScript |
| Testing | pytest 176 tests, vitest 34 tests, Playwright 21 tests |
| Quality | ruff, mypy, TypeScript |

## Quick Start

### Prerequisites

- Python 3.12
- Node.js 22
- Optional: `OPENAI_API_KEY` for LLM-backed analysis

### Backend

```bash
cp .env.example .env
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`.

### Fallback Mode

Leaving `OPENAI_API_KEY` empty is supported. The backend will still parse PDFs, run local keyword/evidence fallbacks, generate reports, and pass the integration tests.

## Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | Optional OpenAI-compatible API key | empty |
| `OPENAI_BASE_URL` | Chat API base URL | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | Default model for new runs | `gpt-4o-mini` |
| `OPENAI_MODEL_OPTIONS` | Comma-separated model options | `gpt-4o-mini,gpt-4o,deepseek-chat` |
| `OPENAI_TIMEOUT_SECONDS` | LLM request timeout | `60` |
| `DATABASE_URL` | SQLite database URL | `sqlite:///./data/paper2repo.db` |
| `UPLOAD_DIR` | Uploaded PDF directory | `./storage/uploads` |
| `REPORT_DIR` | Generated report directory | `./storage/reports` |
| `UPLOAD_MAX_MB` | Single upload size limit | `50` |
| `RUN_STALE_AFTER_MINUTES` | Stale job recovery threshold | `60` |
| `ANALYSIS_MAX_WORKERS` | Batch/recovery worker count | `3` |
| `ANALYSIS_JOB_LEASE_SECONDS` | Job lease duration | `3600` |
| `ANALYSIS_JOB_MAX_ATTEMPTS` | Retry attempts for recoverable jobs | `2` |

## Main API

Swagger UI is available at `http://127.0.0.1:8000/docs`.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/papers/upload` | Upload one PDF |
| `POST` | `/api/papers/upload-batch` | Upload multiple PDFs |
| `POST` | `/api/papers/batch-start` | Start batch analysis |
| `GET` | `/api/papers` | List uploaded papers |
| `GET` | `/api/papers/{paper_id}` | Get paper details |
| `GET` | `/api/papers/{paper_id}/runs` | List runs for one paper |
| `POST` | `/api/papers/{paper_id}/runs` | Start analysis |
| `GET` | `/api/runs` | List runs |
| `GET` | `/api/runs/batches/{batch_id}` | Get batch status |
| `GET` | `/api/runs/{run_id}` | Get run status |
| `DELETE` | `/api/runs/{run_id}` | Delete completed/failed run |
| `POST` | `/api/runs/{run_id}/cancel` | Cancel pending/running run |
| `GET` | `/api/runs/{run_id}/analysis` | Get structured analysis JSON |
| `GET` | `/api/runs/{run_id}/report` | Get Markdown report content |
| `GET` | `/api/runs/{run_id}/report.md` | Download Markdown |
| `GET` | `/api/runs/{run_id}/report.pdf` | Download PDF |
| `GET` | `/api/runs/{run_id}/report.html` | Download HTML |
| `GET` | `/api/runs/{run_id}/report.tex` | Download LaTeX |
| `GET` | `/api/runs/{run_id}/skeleton` | Download code skeleton zip |
| `GET` | `/api/runs/{run_id}/qa` | Get Q&A history |
| `POST` | `/api/runs/{run_id}/qa` | Ask a question |
| `POST` | `/api/runs/{run_id}/qa/stream` | Ask with SSE streaming |
| `GET` | `/api/runs/{run_id}/pwc-links` | Papers With Code links |
| `GET` | `/api/runs/{run_id}/citations` | Extracted citations |
| `GET` | `/api/citations/network` | Citation edges across papers |
| `POST` | `/api/arxiv/import` | Import and analyze arXiv paper |
| `GET` | `/api/arxiv/{id}/versions` | List arXiv versions |
| `POST` | `/api/arxiv/compare` | Compare two arXiv versions |
| `GET` | `/api/compare` | Compare completed runs |
| `GET` | `/api/compare/available` | List comparable runs |
| `GET` | `/api/knowledge/search` | Search knowledge base |
| `GET` | `/api/knowledge/papers` | List indexed papers |
| `GET/PUT` | `/api/settings` | App settings |
| `GET/PUT` | `/api/llm/config` | LLM config |
| `POST` | `/api/llm/check` | Test current model connectivity |

## Frontend Routes

| Route | Description |
| --- | --- |
| `/` | Upload, recent runs, workflow overview |
| `/batch` | Batch PDF upload and batch analysis |
| `/arxiv` | arXiv import/version workflows |
| `/knowledge` | Knowledge-base semantic search |
| `/compare` | Multi-paper comparison |
| `/settings` | UI/report language, model, theme, and model connectivity settings |
| `/runs/[runId]` | Report, Q&A, downloads, citations |
| `/papers/[paperId]` | Paper details and run history |

## Development Checks

Backend:

```bash
cd backend
python -m ruff check app tests
python -m mypy app --ignore-missing-imports
python -m pytest tests -q
```

Frontend:

```bash
cd frontend
npm run lint
npm run test:unit
npm run build
npm run test:e2e
```

Playwright tests are fully mocked for CI stability. Backend integration coverage is handled by pytest.

## GitHub Checklist

- Do not commit `.env`, local SQLite databases, uploaded PDFs, generated reports, `.DS_Store`, `.next`, cache folders, Playwright reports, or local `.docx` project reports.
- Use `.env.example` as the public configuration template.
- Keep `backend/tests/fixtures/sample.pdf`; it is a small test fixture used by integration tests.
- Run all backend and frontend checks before opening a pull request.

## Repository Layout

```text
Paper2Repo/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   └── services/
│   └── tests/
├── frontend/
│   ├── app/
│   ├── e2e/
│   └── lib/
├── docs/
├── .github/workflows/ci.yml
├── docker-compose.yml
└── README.md
```

## License

MIT
