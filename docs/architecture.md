# Paper2Repo Architecture

Paper2Repo is a local-first AI-paper analysis system. It turns PDFs and arXiv papers into evidence-grounded understanding reports, reproduction plans, export files, Q&A sessions, and searchable paper knowledge.

## Data Flow

```text
PDF upload / arXiv import / batch upload
-> papers row
-> run row with selected model and optional batch id
-> recoverable analysis job
-> shared bounded ThreadPoolExecutor
-> LangGraph workflow
-> frontend polling sees progress and completion
-> report, exports, Q&A, citations, skeleton, knowledge search
```

## Analysis Workflow

```text
parse_pdf_node
-> chunk_paper_node
-> extract_citations_node
-> extract_metadata_node
-> classify_paper_type_node
-> understand_paper_node
-> analyze_method_node
-> analyze_experiments_node
-> plan_reproduction_node
-> generate_report_node
-> persist_result_node
```

`parse_pdf_node` and `chunk_paper_node` are critical. Later analysis nodes are recoverable: failures are captured in `node_errors`, downstream nodes continue where possible, and the generated report includes partial results plus error context.

## Main Components

- `backend/app/api`: thin domain routers plus a single aggregated `api_router` used by the FastAPI app. Routers own HTTP validation, status codes, and response shaping, while orchestration lives in services.
- `backend/app/agents`: LangGraph workflow, state definition, prompts, and analysis nodes.
- `backend/app/core`: app lifespan wiring, settings, and compatibility facades for shared app infrastructure.
- `backend/app/repositories`: SQLite-backed data access grouped by persistence concern. This package owns SQL queries and migration helpers; `app.core.database` remains a stable compatibility import surface.
- `backend/app/schemas`: Pydantic contracts for analysis outputs and API responses.
- `backend/app/services`: PDF parsing, upload handling, analysis job orchestration, chunking, retrieval, LLM client, Q&A, code skeletons, and arXiv client.
- `backend/app/services/reports`: Markdown, PDF, HTML, and LaTeX report builders plus report formatting helpers.
- `frontend/app`: Next.js App Router entrypoints and route-level composition.
- `frontend/components`: reusable UI grouped by upload, report, history, knowledge, and shared concerns.
- `frontend/hooks`: client-side language and theme hooks.
- `frontend/lib`: shared types, i18n, polling, and presentation helpers. `frontend/lib/api.ts` is a stable barrel export; implementation is split by backend domain under `frontend/lib/api/`.

## Storage

- SQLite stores papers, chunks, runs, jobs, analysis JSON, reports, settings, Q&A messages, citations, and embeddings.
- Uploaded PDFs and generated reports are local files under configurable storage directories.
- Markdown reports are persisted; PDF, HTML, and LaTeX downloads are generated from stored Markdown content.
- Embeddings are stored in SQLite for local knowledge search; retrieval uses a hybrid semantic/keyword score.

## Background Jobs

- Each run creates a recoverable analysis job.
- Single, batch, arXiv, and recovered runs share one bounded worker pool controlled by `ANALYSIS_MAX_WORKERS`.
- Leases are renewed at workflow progress boundaries; startup and periodic recovery reclaim interrupted jobs that are safe to retry.
- Pending/running runs can be canceled through the API, and cancellation is checked before a run can be finalized as completed.

## Frontend Runtime

- Next.js rewrites `/api/*` to the FastAPI backend during local development.
- The frontend polls run status and renders report/Q&A/download views when a run completes.
- Playwright uses mocked API responses for deterministic UI coverage and a separate real frontend-backend upload/report flow.

## Current Boundaries

- No authentication or multi-user isolation.
- No distributed worker queue; background work is local-process based.
- No external vector database; embeddings are stored in local SQLite.
- Full scientific reproduction is not generated automatically. The code skeleton is a structured starting point with TODOs and acceptance criteria.
