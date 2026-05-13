from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_analysis_result, get_paper, get_report, get_run, list_runs

router = APIRouter(
    prefix="/compare",
    tags=["compare"],
)


@router.get(
    "",
    summary="Compare analysis runs",
    description="Retrieve structured comparison data for multiple completed runs.",
)
def compare_runs(
    run_ids: str = Query(..., description="Comma-separated run IDs to compare"),
) -> list[dict[str, Any]]:
    ids = [rid.strip() for rid in run_ids.split(",") if rid.strip()]
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 run IDs are required.")
    if len(ids) > 4:
        raise HTTPException(status_code=400, detail="At most 4 runs can be compared.")

    results: list[dict[str, Any]] = []
    for run_id in ids:
        run = get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")
        if run["status"] != "completed":
            raise HTTPException(status_code=400, detail=f"Run {run_id} is not completed.")

        paper = get_paper(run["paper_id"])
        analysis = get_analysis_result(run_id)
        report = get_report(run_id)

        metadata = analysis.get("metadata_json") if analysis else {}
        understanding = analysis.get("understanding_json") if analysis else {}
        method = analysis.get("method_json") if analysis else {}
        experiments = analysis.get("experiments_json") if analysis else {}
        reproduction = analysis.get("reproduction_json") if analysis else {}

        results.append({
            "run_id": run_id,
            "paper_id": run["paper_id"],
            "paper_title": paper.get("title") if paper else None,
            "paper_filename": paper.get("filename") if paper else None,
            "model_name": run.get("model_name"),
            "created_at": run.get("created_at"),
            "report_title": report.get("title") if report else None,
            "report_content": report.get("content") if report else None,
            "metadata": _extract_metadata_summary(metadata),
            "understanding": _extract_understanding_summary(understanding),
            "method": _extract_method_summary(method),
            "experiments": _extract_experiments_summary(experiments),
            "reproduction": _extract_reproduction_summary(reproduction),
        })

    return results


@router.get(
    "/available",
    summary="List runs available for comparison",
    description="Retrieve completed runs that can be selected for comparison.",
)
def list_available_runs() -> list[dict[str, Any]]:
    runs = list_runs(limit=50)
    available = []
    for run in runs:
        if run["status"] == "completed":
            paper = get_paper(run["paper_id"])
            available.append({
                "run_id": run["id"],
                "paper_id": run["paper_id"],
                "paper_title": paper.get("title") if paper else None,
                "paper_filename": paper.get("filename") if paper else None,
                "model_name": run.get("model_name"),
                "created_at": run.get("created_at"),
            })
    return available


def _extract_metadata_summary(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    return {
        "title": metadata.get("title", ""),
        "authors": metadata.get("authors", []),
        "venue": metadata.get("venue", ""),
        "year": metadata.get("year", ""),
        "keywords": metadata.get("keywords", []),
    }


def _extract_understanding_summary(understanding: dict[str, Any] | None) -> dict[str, Any]:
    if not understanding:
        return {}
    return {
        "background": understanding.get("background", "")[:300],
        "core_problem": understanding.get("core_problem", "")[:300],
        "main_contributions": understanding.get("main_contributions", [])[:5],
        "overall_idea": understanding.get("overall_idea", "")[:300],
    }


def _extract_method_summary(method: dict[str, Any] | None) -> dict[str, Any]:
    if not method:
        return {}
    return {
        "method_name": method.get("method_name", ""),
        "pipeline_overview": method.get("pipeline_overview", "")[:300],
        "key_innovations": method.get("key_innovations", [])[:5],
        "architecture": method.get("architecture", "")[:300],
        "loss_functions": method.get("loss_functions", [])[:3],
        "training_strategy": method.get("training_strategy", "")[:200],
    }


def _extract_experiments_summary(experiments: dict[str, Any] | None) -> dict[str, Any]:
    if not experiments:
        return {}
    return {
        "datasets": [d.get("name", "") for d in experiments.get("datasets", [])],
        "metrics": experiments.get("metrics", [])[:5],
        "baselines": experiments.get("baselines", [])[:5],
        "main_results": experiments.get("main_results", [])[:5],
    }


def _extract_reproduction_summary(reproduction: dict[str, Any] | None) -> dict[str, Any]:
    if not reproduction:
        return {}
    return {
        "reproduction_goal": reproduction.get("reproduction_goal", "")[:300],
        "estimated_effort": reproduction.get("estimated_effort", ""),
        "risks": reproduction.get("risks", [])[:3],
        "checklist": reproduction.get("checklist", [])[:5],
    }
