# Contributing to Paper2Repo

Thanks for taking the time to improve Paper2Repo. The project is focused on one product contract: turn research papers into evidence-grounded understanding and reproduction plans, not generic summaries.

## Good First Contributions

- Improve setup, Docker, or documentation clarity.
- Add small UI fixes that make the local workspace easier to use.
- Improve report quality, citations, evidence references, or reproduction checklists.
- Add regression tests for PDF parsing, workflow recovery, report export, or frontend rendering.
- Share a reproducible paper case study with expected outputs and edge cases.

## Local Setup

The fastest path is Docker:

```bash
cp .env.example .env
docker compose up --build
```

Manual development is also supported:

```bash
cp .env.example .env

cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload

cd ../frontend
npm ci
npm run dev
```

`OPENAI_API_KEY` is optional. Without it, Paper2Repo still runs deterministic local fallbacks for parsing, evidence extraction, and report generation.

## Before Opening a Pull Request

Run the checks that match your change:

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

If a check is unrelated or cannot run in your environment, mention that in the pull request.

## Pull Request Guidelines

- Keep changes focused and explain the user-facing effect.
- Preserve the local-first workflow and the no-key fallback path.
- Avoid committing local files such as `.env`, SQLite databases, uploaded PDFs, generated reports, `.next`, Playwright reports, or caches.
- Include screenshots or short clips for visible UI changes.
- Add or update tests when changing backend contracts, workflow nodes, report generation, exports, or frontend data rendering.

## Issue Guidelines

For bugs, include the input type, the failing step, expected behavior, actual behavior, logs if available, and whether `OPENAI_API_KEY` was set.

For feature requests, describe the research or reproduction workflow you want to support, not only the UI control you want added.
