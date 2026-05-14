# Paper2Repo Architecture

Paper2Repo is a local-first AI-paper analysis system. It turns PDFs and arXiv papers into evidence-grounded understanding reports, reproduction plans, export files, Q&A sessions, and searchable paper knowledge.

## Data Flow

```text
PDF upload / arXiv import / batch upload
-> papers row
-> run row with selected model and optional batch id
-> recoverable analysis job
-> FastAPI BackgroundTasks / ThreadPoolExecutor
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

- `backend/app/api`: FastAPI routers for papers, runs, reports, Q&A, arXiv, comparison, citations, knowledge search, settings, and LLM config.
- `backend/app/agents`: LangGraph workflow, state definition, prompts, and analysis nodes.
- `backend/app/core`: settings and SQLite persistence.
- `backend/app/schemas`: Pydantic contracts for analysis outputs and API responses.
- `backend/app/services`: PDF parsing, chunking, retrieval, LLM client, report exporters, Q&A, code skeletons, and arXiv client.
- `frontend/app`: Next.js App Router pages and client components.
- `frontend/lib`: API client, shared types, i18n, presentation helpers.

## Storage

- SQLite stores papers, chunks, runs, jobs, analysis JSON, reports, settings, Q&A messages, citations, and embeddings.
- Uploaded PDFs and generated reports are local files under configurable storage directories.
- Markdown reports are persisted; PDF, HTML, and LaTeX downloads are generated from stored Markdown content.
- Embeddings are stored in SQLite for local knowledge search; retrieval uses a hybrid semantic/keyword score.

## Background Jobs

- Each run creates a recoverable analysis job.
- Startup recovery reclaims unfinished jobs that are safe to retry.
- Batch analysis uses a bounded worker pool controlled by `ANALYSIS_MAX_WORKERS`.
- Pending/running runs can be canceled through the API.

## Frontend Runtime

- Next.js rewrites `/api/*` to the FastAPI backend during local development.
- The frontend polls run status and renders report/Q&A/download views when a run completes.
- Playwright tests mock API responses for CI stability; backend integration behavior is covered by pytest.

## Current Boundaries

- No authentication or multi-user isolation.
- No distributed worker queue; background work is local-process based.
- No external vector database; embeddings are stored in local SQLite.
- Full scientific reproduction is not generated automatically. The code skeleton is a structured starting point with TODOs and acceptance criteria.
