# Paper2Repo API

## Health

`GET /health`

Returns service status.

## Papers

`POST /api/papers/upload`

Multipart form upload with field `file`.

`GET /api/papers`

Returns uploaded papers.

`GET /api/papers/{paper_id}`

Returns one paper.

## Runs

`POST /api/papers/{paper_id}/runs`

Starts a synchronous MVP analysis run.

`GET /api/runs/{run_id}`

Returns run status.

`GET /api/runs/{run_id}/analysis`

Returns structured JSON analysis results.

`GET /api/runs/{run_id}/report`

Returns Markdown report content and local report path.
