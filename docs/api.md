# Paper2Repo API

Paper2Repo exposes a local FastAPI API for PDF upload, background analysis runs, structured results, and report downloads.

## Health

- `GET /health`

Returns service status.

## Papers

- `POST /api/papers/upload`

Uploads a PDF with multipart field `file`. Returns the saved paper record.

- `GET /api/papers`

Returns uploaded papers.

- `GET /api/papers/{paper_id}`

Returns one uploaded paper.

## Runs

- `POST /api/papers/{paper_id}/runs`

Creates a run immediately and starts the LangGraph workflow in a FastAPI background task. The response includes `run_id`, `status`, `current_step`, `progress_percent`, and `model_name`.

- `GET /api/runs`

Returns recent runs. Optional query parameters:

```text
paper_id=<paper id>
limit=20
```

- `GET /api/runs/{run_id}`

Returns run status for frontend polling.

- `GET /api/runs/{run_id}/analysis`

Returns structured JSON analysis results after the workflow persists output.

## Reports

- `GET /api/runs/{run_id}/report`

Returns Markdown report content as JSON.

- `GET /api/runs/{run_id}/report.md`

Downloads the Markdown report as a file.

- `GET /api/runs/{run_id}/report.pdf`

Downloads a generated PDF copy of the report.

## LLM Config

- `GET /api/llm/config`

Returns whether the OpenAI-compatible API is configured, current `base_url`, default model, and available models.

- `PUT /api/llm/config`

Updates the global default model for new runs. Request body:

```json
{
  "default_model": "deepseek-chat"
}
```
