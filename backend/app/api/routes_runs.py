from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.database import get_analysis_result, get_report, get_run
from app.schemas.paper import RunResponse

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}", response_model=RunResponse)
def get_run_detail(run_id: str) -> RunResponse:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    return RunResponse(**run)


@router.get("/{run_id}/analysis")
def get_run_analysis(run_id: str) -> dict:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    result = get_analysis_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis result not found.")

    return {
        "run_id": run_id,
        "paper_id": result["paper_id"],
        "metadata": result["metadata_json"],
        "classification": result["classification_json"],
        "understanding": result["understanding_json"],
        "method_analysis": result["method_json"],
        "experiment_analysis": result["experiments_json"],
        "reproduction_plan": result["reproduction_json"],
    }


@router.get("/{run_id}/report")
def get_run_report(run_id: str) -> dict:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    report = get_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    return {
        "run_id": run_id,
        "paper_id": report["paper_id"],
        "title": report["title"],
        "content": report["content"],
        "file_path": report["file_path"],
        "created_at": report["created_at"],
    }
