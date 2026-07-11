from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.core.config import get_settings
from app.core.database import (
    create_analysis_job,
    create_batch_id,
    create_paper,
    create_run,
    delete_paper,
    delete_run,
    get_paper,
    list_papers,
    list_runs,
)
from app.schemas.paper import BatchStartResponse, BatchUploadResponse, PaperResponse, RunListItemResponse, RunResponse
from app.services import analysis_runner
from app.services.storage_maintenance import delete_managed_file
from app.services.uploads import save_pdf_upload, save_pdf_uploads

router = APIRouter(
    prefix="/papers",
    tags=["papers"],
    responses={404: {"description": "Paper not found"}},
)


@router.post(
    "/upload",
    response_model=PaperResponse,
    summary="Upload a PDF paper",
    description="Upload a PDF file for analysis. Validates file type (PDF only) and size limit.",
)
def upload_paper(file: UploadFile = File(...)) -> PaperResponse:
    settings = get_settings()
    saved = save_pdf_upload(file, settings.upload_path, settings.upload_max_bytes)
    paper = create_paper(filename=saved.filename, file_path=saved.file_path, file_size=saved.file_size)
    return PaperResponse(**paper)


@router.get(
    "",
    response_model=list[PaperResponse],
    summary="List uploaded papers",
    description="Retrieve a list of all uploaded papers, ordered by upload time.",
)
def get_papers() -> list[PaperResponse]:
    return [PaperResponse(**paper) for paper in list_papers()]


@router.get(
    "/{paper_id}",
    response_model=PaperResponse,
    summary="Get paper details",
    description="Retrieve details of an uploaded paper by ID.",
)
def get_paper_detail(paper_id: str) -> PaperResponse:
    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return PaperResponse(**paper)


@router.delete(
    "/{paper_id}",
    response_model=PaperResponse,
    summary="Delete a paper",
    description=(
        "Delete a paper and all completed/failed analysis data, reports, chunks, "
        "embeddings, citations, usage records, and managed local files."
    ),
)
def delete_paper_detail(paper_id: str) -> PaperResponse:
    deletion = delete_paper(paper_id)
    if deletion.status == "not_found":
        raise HTTPException(status_code=404, detail="Paper not found.")
    if deletion.status == "active_runs":
        raise HTTPException(status_code=409, detail="Paper has pending or running analyses.")
    if deletion.paper is None:
        raise RuntimeError("Paper deletion completed without the deleted paper record.")

    upload_path = str(deletion.paper["file_path"])
    for path in deletion.storage_paths:
        area = "uploads" if path == upload_path else "reports"
        delete_managed_file(path, area=area)
    return PaperResponse(**deletion.paper)


@router.get(
    "/{paper_id}/runs",
    response_model=list[RunListItemResponse],
    summary="List runs for a paper",
    description="Retrieve all analysis runs for a specific paper.",
)
def get_paper_runs(paper_id: str) -> list[RunListItemResponse]:
    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return [RunListItemResponse(**run) for run in list_runs(paper_id=paper_id)]


@router.post(
    "/{paper_id}/runs",
    response_model=RunResponse,
    summary="Start analysis",
    description="Start a new analysis run for the paper. The analysis runs in the background.",
)
def start_run(paper_id: str) -> RunResponse:
    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    run = create_run(paper_id)
    create_analysis_job(run["id"], paper_id)
    try:
        analysis_runner.submit_analysis(paper_id, run["id"], paper["file_path"], run.get("model_name"))
    except analysis_runner.AnalysisQueueFullError as exc:
        delete_run(run["id"])
        raise HTTPException(status_code=503, detail=str(exc), headers={"Retry-After": "5"}) from exc
    return RunResponse(**run)


MAX_BATCH_FILE_SIZE = 50 * 1024 * 1024  # 50MB per file
MAX_BATCH_TOTAL_SIZE = 200 * 1024 * 1024  # 200MB total


@router.post(
    "/upload-batch",
    response_model=BatchUploadResponse,
    summary="Upload multiple PDFs",
    description="Upload multiple PDF files for batch analysis. Max 50MB per file, 200MB total.",
)
def upload_batch(files: list[UploadFile] = File(...)) -> BatchUploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files per batch.")

    settings = get_settings()
    saved_uploads = save_pdf_uploads(files, settings.upload_path, MAX_BATCH_FILE_SIZE, MAX_BATCH_TOTAL_SIZE)
    uploaded: list[PaperResponse] = []
    for saved in saved_uploads:
        paper = create_paper(filename=saved.filename, file_path=saved.file_path, file_size=saved.file_size)
        uploaded.append(PaperResponse(**paper))

    return BatchUploadResponse(papers=uploaded)


@router.post(
    "/batch-start",
    response_model=BatchStartResponse,
    summary="Start batch analysis",
    description="Start parallel analysis for multiple papers using the configured bounded worker queue.",
)
def start_batch(
    paper_ids: str = Query(..., description="Comma-separated paper IDs"),
) -> BatchStartResponse:
    ids = [pid.strip() for pid in paper_ids.split(",") if pid.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="No paper IDs provided.")

    batch_id = create_batch_id()
    runs: list[RunResponse] = []
    tasks: list[analysis_runner.AnalysisRunRequest] = []
    papers = []

    for pid in ids:
        paper = get_paper(pid)
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper not found: {pid}")
        papers.append((pid, paper))

    for pid, paper in papers:
        run = create_run(pid, batch_id=batch_id)
        create_analysis_job(run["id"], pid)
        tasks.append(
            analysis_runner.AnalysisRunRequest(
                paper_id=pid,
                run_id=run["id"],
                pdf_path=paper["file_path"],
                model_name=run.get("model_name"),
            )
        )
        runs.append(RunResponse(**run))

    try:
        analysis_runner.submit_batch_analysis(tasks)
    except analysis_runner.AnalysisQueueFullError as exc:
        for run_response in runs:
            delete_run(run_response.id)
        raise HTTPException(status_code=503, detail=str(exc), headers={"Retry-After": "5"}) from exc
    return BatchStartResponse(batch_id=batch_id, runs=runs)
