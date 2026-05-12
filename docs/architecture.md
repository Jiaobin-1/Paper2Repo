# Paper2Repo Architecture

Paper2Repo is a local MVP for turning AI paper PDFs into structured understanding reports and actionable reproduction plans.

## Data Flow

```text
PDF upload
-> papers row
-> run row with selected model
-> FastAPI BackgroundTasks starts LangGraph workflow
-> parse_pdf_node
-> chunk_paper_node
-> extract_metadata_node
-> classify_paper_type_node
-> understand_paper_node
-> analyze_method_node
-> analyze_experiments_node
-> plan_reproduction_node
-> generate_report_node
-> persist_result_node
-> frontend polling sees completed run
-> Markdown / PDF report display and download
```

## Main Components

- `backend/app/api`: FastAPI routers for papers, runs, reports, and LLM config.
- `backend/app/core`: settings and SQLite helpers.
- `backend/app/schemas`: Pydantic output contracts.
- `backend/app/services`: PDF parser, chunker, retrieval, LLM client, Markdown exporter, PDF exporter.
- `backend/app/agents`: LangGraph state, graph, and workflow nodes.
- `frontend/app`: Next.js App Router pages and client components.

## Workflow Notes

- Analysis runs are background tasks, not synchronous request work.
- The frontend polls `GET /api/runs/{run_id}` for `current_step` and `progress_percent`.
- `retrieve_context` is a helper used inside analysis nodes, not a LangGraph node.
- LLM calls use OpenAI-compatible Chat Completions through environment variables.
- If no API key is configured, nodes use local keyword-based fallback outputs.
- The selected model is saved as a global default and copied into each new run.

## Storage

- SQLite stores papers, chunks, runs, structured analysis JSON, reports, and app settings.
- Uploaded PDFs and generated Markdown reports are local files.
- Report PDF downloads are generated from saved Markdown content on demand.

## MVP Constraints

- No automatic web search.
- No vector database.
- No full reproduction repository generation.
- No login or multi-user isolation.
- No distributed worker queue.
- No complex frontend animation.
