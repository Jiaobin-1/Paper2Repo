from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile

from app.agents.graph import run_analysis
from app.core.config import get_settings
from app.core.database import (
    claim_analysis_job,
    complete_analysis_job,
    create_analysis_job,
    create_batch_id,
    create_paper,
    create_run,
    fail_analysis_job,
    get_paper,
    get_run,
    is_analysis_cancel_requested,
    list_papers,
    list_recoverable_analysis_jobs,
    list_runs,
    update_run_status,
)
from app.schemas.paper import BatchStartResponse, BatchUploadResponse, PaperResponse, RunListItemResponse, RunResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/papers",
    tags=["papers"],
    responses={404: {"description": "Paper not found"}},
)
PDF_SIGNATURE = b"%PDF-"
UPLOAD_CHUNK_SIZE = 1024 * 1024
_recovery_executor: ThreadPoolExecutor | None = None


def run_analysis_background(paper_id: str, run_id: str, pdf_path: str, model_name: str | None) -> None:
    def record_progress(current_step: str, progress_percent: int) -> None:
        if is_analysis_cancel_requested(run_id):
            raise RuntimeError("Analysis canceled.")
        update_run_status(
            run_id,
            "running",
            current_step=current_step,
            progress_percent=progress_percent,
        )

    try:
        claim_status = claim_analysis_job(run_id)
        if claim_status == "completed":
            return
        if claim_status == "canceled":
            update_run_status(
                run_id,
                "failed",
                error_message="Analysis canceled.",
                completed=True,
                current_step="failed",
            )
            return
        update_run_status(run_id, "running", current_step="queued", progress_percent=0)
        run_analysis(
            paper_id=paper_id,
            run_id=run_id,
            pdf_path=pdf_path,
            model_name=model_name,
            progress_callback=record_progress,
        )
        update_run_status(
            run_id,
            "completed",
            completed=True,
            current_step="completed",
            progress_percent=100,
        )
        complete_analysis_job(run_id)
    except Exception as exc:
        logger.exception("Analysis failed for run %s", run_id)
        try:
            job_status = fail_analysis_job(run_id, str(exc))
            if job_status == "pending":
                update_run_status(run_id, "pending", error_message=str(exc), current_step="queued")
            elif job_status == "canceled":
                update_run_status(
                    run_id,
                    "failed",
                    error_message="Analysis canceled.",
                    completed=True,
                    current_step="failed",
                )
            else:
                update_run_status(
                    run_id,
                    "failed",
                    error_message=str(exc),
                    completed=True,
                    current_step="failed",
                )
        except Exception:
            logger.exception("Failed to update run status after error for run %s", run_id)


def start_recoverable_analysis_jobs() -> None:
    global _recovery_executor
    jobs = list_recoverable_analysis_jobs()
    if not jobs:
        return
    settings = get_settings()
    if _recovery_executor is None:
        _recovery_executor = ThreadPoolExecutor(max_workers=max(1, settings.analysis_max_workers))
    for job in jobs:
        paper = get_paper(job["paper_id"])
        run = get_run(job["run_id"])
        if not paper:
            fail_analysis_job(job["run_id"], "Paper record was not found during recovery.")
            continue
        _recovery_executor.submit(
            run_analysis_background,
            job["paper_id"],
            job["run_id"],
            paper["file_path"],
            run.get("model_name") if run else None,
        )


@router.post(
    "/upload",
    response_model=PaperResponse,
    summary="Upload a PDF paper",
    description="Upload a PDF file for analysis. Validates file type (PDF only) and size limit.",
)
def upload_paper(file: UploadFile = File(...)) -> PaperResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    settings = get_settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    if len(safe_name) > 200:
        suffix = Path(safe_name).suffix[:10]
        safe_name = safe_name[:200 - len(suffix)] + suffix
    stored_name = f"{uuid.uuid4()}_{safe_name}"
    file_path = settings.upload_path / stored_name

    try:
        file_size = _save_limited_upload(file, file_path, settings.upload_max_bytes)
        _validate_pdf_signature(file_path)
    except HTTPException:
        _delete_if_exists(file_path)
        raise
    except Exception as exc:
        _delete_if_exists(file_path)
        raise HTTPException(status_code=400, detail="Failed to save uploaded PDF.") from exc
    finally:
        file.file.close()

    paper = create_paper(filename=safe_name, file_path=file_path, file_size=file_size)
    return PaperResponse(**paper)


def _save_limited_upload(file: UploadFile, file_path: Path, max_bytes: int) -> int:
    total_size = 0
    with file_path.open("wb") as buffer:
        while True:
            chunk = file.file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_bytes:
                max_mb = max_bytes // (1024 * 1024)
                raise HTTPException(status_code=400, detail=f"PDF file is too large. Maximum size is {max_mb} MB.")
            buffer.write(chunk)
    return total_size


def _validate_pdf_signature(file_path: Path) -> None:
    with file_path.open("rb") as saved_file:
        if saved_file.read(len(PDF_SIGNATURE)) != PDF_SIGNATURE:
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF.")


def _delete_if_exists(file_path: Path) -> None:
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Failed to remove partial upload %s", file_path, exc_info=True)


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
def start_run(paper_id: str, background_tasks: BackgroundTasks) -> RunResponse:
    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    run = create_run(paper_id)
    create_analysis_job(run["id"], paper_id)
    background_tasks.add_task(run_analysis_background, paper_id, run["id"], paper["file_path"], run.get("model_name"))
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
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    total_size = 0
    uploaded: list[PaperResponse] = []

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"Only PDF files are supported. Rejected: {file.filename}")

        safe_name = Path(file.filename).name
        if len(safe_name) > 200:
            suffix = Path(safe_name).suffix[:10]
            safe_name = safe_name[:200 - len(suffix)] + suffix
        stored_name = f"{uuid.uuid4()}_{safe_name}"
        file_path = settings.upload_path / stored_name

        try:
            file_size = _save_limited_upload(file, file_path, MAX_BATCH_FILE_SIZE)
            total_size += file_size
            if total_size > MAX_BATCH_TOTAL_SIZE:
                _delete_if_exists(file_path)
                raise HTTPException(status_code=400, detail=f"Total batch size exceeds {MAX_BATCH_TOTAL_SIZE // (1024 * 1024)} MB limit.")
            _validate_pdf_signature(file_path)
        except HTTPException:
            _delete_if_exists(file_path)
            raise
        except Exception as exc:
            _delete_if_exists(file_path)
            raise HTTPException(status_code=400, detail="Failed to save uploaded PDF.") from exc
        finally:
            file.file.close()

        paper = create_paper(filename=safe_name, file_path=file_path, file_size=file_size)
        uploaded.append(PaperResponse(**paper))

    return BatchUploadResponse(papers=uploaded)


@router.post(
    "/batch-start",
    response_model=BatchStartResponse,
    summary="Start batch analysis",
    description="Start parallel analysis for multiple papers. Uses thread pool with max 3 workers.",
)
def start_batch(
    paper_ids: str = Query(..., description="Comma-separated paper IDs"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> BatchStartResponse:
    ids = [pid.strip() for pid in paper_ids.split(",") if pid.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="No paper IDs provided.")

    batch_id = create_batch_id()
    runs: list[RunResponse] = []

    for pid in ids:
        paper = get_paper(pid)
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper not found: {pid}")
        run = create_run(pid, batch_id=batch_id)
        create_analysis_job(run["id"], pid)
        runs.append(RunResponse(**run))

    def _run_batch() -> None:
        max_workers = max(1, get_settings().analysis_max_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for pid, run_resp in zip(ids, runs, strict=False):
                paper = get_paper(pid)
                if paper:
                    futures.append(
                        executor.submit(
                            run_analysis_background,
                            pid,
                            run_resp.id,
                            paper["file_path"],
                            run_resp.model_name,
                        )
                    )
            for future in futures:
                try:
                    future.result()
                except Exception:
                    logger.exception("Batch analysis task failed")

    background_tasks.add_task(_run_batch)
    return BatchStartResponse(batch_id=batch_id, runs=runs)
