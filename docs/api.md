# Paper2Repo API

Paper2Repo exposes a local FastAPI API for uploads, background analysis, reports, exports, Q&A, citations, knowledge search, comparison, and settings.

Start the backend and open `http://127.0.0.1:8000/docs` for Swagger UI.

## Health

- `GET /health`

## Papers

- `POST /api/papers/upload`: upload one PDF.
- `POST /api/papers/upload-batch`: upload multiple PDFs.
- `POST /api/papers/batch-start`: start analysis for comma-separated `paper_ids`.
- `GET /api/papers`: list uploaded papers.
- `GET /api/papers/{paper_id}`: get one paper.
- `GET /api/papers/{paper_id}/runs`: list runs for one paper.
- `POST /api/papers/{paper_id}/runs`: start one analysis run.

## Runs And Reports

- `GET /api/runs`: list runs, optionally `paper_id` and `limit`.
- `GET /api/runs/batches/{batch_id}`: get batch status.
- `GET /api/runs/{run_id}`: get run status.
- `DELETE /api/runs/{run_id}`: delete a completed or failed run.
- `POST /api/runs/{run_id}/cancel`: cancel a pending or running run.
- `GET /api/runs/{run_id}/analysis`: get structured analysis JSON.
- `GET /api/runs/{run_id}/report`: get report content as JSON.
- `GET /api/runs/{run_id}/report.md`: download Markdown.
- `GET /api/runs/{run_id}/report.pdf`: download PDF.
- `GET /api/runs/{run_id}/report.html`: download HTML.
- `GET /api/runs/{run_id}/report.tex`: download LaTeX.
- `GET /api/runs/{run_id}/skeleton`: download code skeleton zip.

## Q&A

- `GET /api/runs/{run_id}/qa`: get conversation history.
- `POST /api/runs/{run_id}/qa`: ask a question.
- `POST /api/runs/{run_id}/qa/stream`: ask a question with SSE streaming.

## arXiv

- `POST /api/arxiv/import`: download and analyze by arXiv ID or URL.
- `GET /api/arxiv/{id}/versions`: list available versions.
- `POST /api/arxiv/compare`: download and start analysis for two versions.

## Knowledge, Comparison, And Citations

- `GET /api/knowledge/search`: search indexed paper chunks.
- `GET /api/knowledge/papers`: list indexed papers.
- `GET /api/compare/available`: list comparable completed runs.
- `GET /api/compare`: compare selected runs.
- `GET /api/runs/{run_id}/citations`: get citations extracted for a run.
- `GET /api/citations/network`: build citation edges across selected papers.
- `GET /api/runs/{run_id}/pwc-links`: get Papers With Code links.

## Settings

- `GET /api/settings`: get UI/report/model/theme settings.
- `PUT /api/settings`: update app settings.
- `GET /api/llm/config`: get LLM configuration.
- `PUT /api/llm/config`: update the default model.
- `POST /api/llm/check`: run a short model connectivity check for the current default model.
