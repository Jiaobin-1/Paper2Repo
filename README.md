# Paper2Repo

Turn research papers into evidence-grounded reproduction plans.

[![CI](https://github.com/Jiaobin-1/Paper2Repo/actions/workflows/ci.yml/badge.svg)](https://github.com/Jiaobin-1/Paper2Repo/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![Next.js](https://img.shields.io/badge/Next.js-16-000000)
![License](https://img.shields.io/badge/license-MIT-green)

Paper2Repo is a local-first agent system for reading AI papers and turning them into practical reproduction artifacts. Upload a PDF or import an arXiv paper, run the LangGraph workflow, and get a structured report that connects paper understanding, method and experiment breakdown, evidence references, risks, and a minimal code skeleton plan.

It works without an API key through deterministic local fallbacks. With `OPENAI_API_KEY`, the same workflow uses an OpenAI-compatible chat API for richer analysis and Q&A.

## What It Does

| Capability | Output |
| --- | --- |
| Paper understanding | Background, core problem, contributions, assumptions, limitations |
| Method and experiment audit | Modules, datasets, metrics, baselines, protocols, missing details |
| Reproduction planning | Minimum reproduction goal, scope, risks, checklist, code skeleton |
| Local workspace features | Batch analysis, arXiv import, Q&A, citations, knowledge search, comparison |

## Workflow

```text
PDF / arXiv
  -> parse and chunk paper
  -> extract citations and metadata
  -> understand paper
  -> analyze method and experiments
  -> plan reproduction
  -> export report and code skeleton
```

## Quick Start

### Backend

```bash
cp .env.example .env
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`.

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | Optional OpenAI-compatible API key | empty |
| `OPENAI_BASE_URL` | Chat API base URL | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | Default model for new runs | `gpt-4o-mini` |
| `OPENAI_MODEL_OPTIONS` | Comma-separated model options | `gpt-4o-mini,gpt-4o,deepseek-chat` |
| `OPENAI_TIMEOUT_SECONDS` | LLM request timeout | `60` |
| `DATABASE_URL` | SQLite database URL | `sqlite:///./data/paper2repo.db` |
| `UPLOAD_MAX_MB` | Single upload size limit | `50` |

Leaving `OPENAI_API_KEY` empty is supported. The app still parses PDFs, runs local evidence-based fallbacks, generates reports, and passes the integration tests.

## Project Structure

```text
Paper2Repo/
├── backend/      FastAPI, LangGraph workflow, SQLite persistence
├── frontend/     Next.js app, report UI, settings, batch tools
├── docs/         API, architecture notes, sample report
└── .github/      CI workflow
```

## Documentation

- [API reference](docs/api.md)
- [Architecture](docs/architecture.md)
- [Sample report](docs/examples/sample_report.md)

## Development

```bash
cd backend
python -m ruff check app tests
python -m mypy app --ignore-missing-imports
python -m pytest tests -q

cd ../frontend
npm run lint
npm run test:unit
npm run build
npm run test:e2e
```

Current local verification baseline:

- `pytest`: 176 tests
- `vitest`: 34 tests
- `Playwright`: 21 tests

## Repository Hygiene

Do not commit `.env`, local SQLite databases, uploaded PDFs, generated reports, `.next`, cache folders, Playwright reports, or local document drafts. Use `.env.example` as the public configuration template.

## License

MIT
