from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query, Response

from app.core.database import get_analysis_result, get_report, get_run, list_runs
from app.schemas.paper import RunListItemResponse, RunResponse
from app.services.pdf_exporter import build_report_pdf

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=list[RunListItemResponse])
def get_runs(
    paper_id: str | None = None,
    limit: int = Query(20, ge=1, le=100),
) -> list[RunListItemResponse]:
    return [RunListItemResponse(**run) for run in list_runs(paper_id=paper_id, limit=limit)]


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


@router.get("/{run_id}/report.md")
def download_run_report_markdown(run_id: str) -> Response:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    report = get_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    filename = _safe_report_filename(report["title"], run_id, "md")
    return Response(
        content=report["content"],
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{run_id}/report.pdf")
def download_run_report_pdf(run_id: str) -> Response:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    report = get_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    pdf_bytes = build_report_pdf(title=report["title"], markdown=report["content"])
    filename = _safe_report_filename(report["title"], run_id, "pdf")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _safe_report_filename(title: str, run_id: str, extension: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("._")
    if not cleaned:
        cleaned = f"paper2repo_report_{run_id[:8]}"
    return f"{cleaned[:80]}.{extension}"
