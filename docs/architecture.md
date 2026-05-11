# Paper2Repo Architecture

Paper2Repo MVP uses a synchronous FastAPI request to run a LangGraph workflow over one uploaded PDF.

## Data Flow

```text
PDF upload
-> papers row
-> run row
-> PDF parsing
-> chunk creation
-> structured placeholder analysis
-> reproduction plan
-> Markdown report
-> SQLite persistence
```

## Main Components

- `backend/app/api`: FastAPI routers.
- `backend/app/core`: settings and SQLite helpers.
- `backend/app/schemas`: Pydantic output contracts.
- `backend/app/services`: parser, chunker, retrieval, LLM client, Markdown exporter.
- `backend/app/agents`: LangGraph state, graph, and nodes.
- `frontend/app`: minimal Next.js pages.

## MVP Constraints

- No automatic web search.
- No vector database.
- No full reproduction repository generation.
- No background worker.
- No complex frontend animation.
