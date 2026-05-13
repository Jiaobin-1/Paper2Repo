from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse

from app.core.database import delete_run, get_analysis_result, get_report, get_run, list_runs
from app.schemas.paper import RunListItemResponse, RunResponse
from app.services.code_skeleton import generate_skeleton_zip
from app.services.pdf_exporter import build_report_pdf

router = APIRouter(
    prefix="/runs",
    tags=["runs"],
    responses={404: {"description": "Run not found"}},
)


@router.get(
    "",
    response_model=list[RunListItemResponse],
    summary="List analysis runs",
    description="Retrieve a list of analysis runs, optionally filtered by paper ID.",
)
def get_runs(
    paper_id: str | None = Query(None, description="Filter by paper ID"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
) -> list[RunListItemResponse]:
    return [RunListItemResponse(**run) for run in list_runs(paper_id=paper_id, limit=limit)]


@router.get(
    "/{run_id}",
    response_model=RunResponse,
    summary="Get run details",
    description="Retrieve the current status and details of an analysis run.",
)
def get_run_detail(run_id: str) -> RunResponse:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    return RunResponse(**run)


@router.delete(
    "/{run_id}",
    response_model=RunResponse,
    summary="Delete a run",
    description="Delete an analysis run and its associated report. Cannot delete running analyses.",
)
def delete_run_detail(run_id: str) -> RunResponse:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run["status"] in {"pending", "running"}:
        raise HTTPException(status_code=409, detail="Running analysis cannot be deleted.")
    report = get_report(run_id)
    deleted_run = delete_run(run_id)
    if not deleted_run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if report and report.get("file_path"):
        Path(report["file_path"]).unlink(missing_ok=True)
    return RunResponse(**deleted_run)


@router.get(
    "/{run_id}/analysis",
    summary="Get analysis results",
    description="Retrieve the structured analysis results including metadata, classification, understanding, method analysis, experiments, and reproduction plan.",
)
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


@router.get(
    "/{run_id}/report",
    summary="Get report content",
    description="Retrieve the generated Markdown report content.",
)
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


@router.get(
    "/{run_id}/report.md",
    summary="Download Markdown report",
    description="Download the report as a Markdown file.",
)
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


@router.get(
    "/{run_id}/report.pdf",
    summary="Download PDF report",
    description="Download the report as a PDF file with Chinese font support.",
)
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


@router.get(
    "/{run_id}/skeleton",
    summary="Download code skeleton",
    description="Generate and download a project skeleton zip from the reproduction plan.",
)
def download_skeleton(run_id: str) -> FileResponse:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run["status"] != "completed":
        raise HTTPException(status_code=400, detail="Run is not completed.")

    try:
        zip_path = generate_skeleton_zip(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"skeleton_{run_id[:8]}.zip",
    )
