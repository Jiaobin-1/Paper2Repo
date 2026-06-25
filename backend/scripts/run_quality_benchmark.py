from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from app.agents.graph import run_analysis
from app.core.config import get_settings
from app.core.database import create_paper, create_run, init_db
from app.services import retrieval
from app.services.quality_benchmark import evaluate_analysis_quality

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = BACKEND_ROOT / "benchmarks" / "quality_cases.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Paper2Repo report-quality benchmarks.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    results = [_run_case(case) for case in cases]
    payload = {
        "passed": all(result["passed"] for result in results),
        "case_count": len(results),
        "average_score": round(sum(result["score"] for result in results) / max(1, len(results)), 4),
        "results": results,
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if payload["passed"] else 1


def _run_case(case: dict) -> dict:
    pdf_path = (BACKEND_ROOT / case["pdf"]).resolve()
    with tempfile.TemporaryDirectory(prefix="paper2repo-quality-") as temp_dir:
        root = Path(temp_dir)
        os.environ.update(
            {
                "DATABASE_URL": f"sqlite:///{root / 'paper2repo.db'}",
                "UPLOAD_DIR": str(root / "uploads"),
                "REPORT_DIR": str(root / "reports"),
                "OPENAI_API_KEY": "",
                "OPENAI_MODEL": "benchmark-fallback",
                "OPENAI_MODEL_OPTIONS": "benchmark-fallback",
                "PDF_OCR_ENABLED": "false",
            }
        )
        get_settings.cache_clear()
        retrieval._HAS_EMBEDDINGS = False
        init_db()
        paper = create_paper(pdf_path.name, pdf_path, pdf_path.stat().st_size)
        run = create_run(paper["id"], model_name="benchmark-fallback")
        state = run_analysis(
            paper_id=paper["id"],
            run_id=run["id"],
            pdf_path=str(pdf_path),
            model_name="benchmark-fallback",
        )
        result = evaluate_analysis_quality(state, case)
        result["id"] = case["id"]
        return result


if __name__ == "__main__":
    raise SystemExit(main())
