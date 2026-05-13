from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.agents.graph import run_analysis
from app.core.config import get_settings
from app.core.database import (
    create_paper,
    create_run,
    get_paper,
    list_papers,
    list_runs,
    update_run_status,
)
from app.schemas.paper import PaperResponse, RunListItemResponse, RunResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/papers",
    tags=["papers"],
    responses={404: {"description": "Paper not found"}},
)
PDF_SIGNATURE = b"%PDF-"
UPLOAD_CHUNK_SIZE = 1024 * 1024


def run_analysis_background(paper_id: str, run_id: str, pdf_path: str, model_name: str | None) -> None:
    def record_progress(current_step: str, progress_percent: int) -> None:
        update_run_status(
            run_id,
            "running",
            current_step=current_step,
            progress_percent=progress_percent,
        )

    try:
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
    except Exception as exc:
        logger.exception("Analysis failed for run %s", run_id)
        try:
            update_run_status(
                run_id,
                "failed",
                error_message=str(exc),
                completed=True,
                current_step="failed",
            )
        except Exception:
            logger.exception("Failed to update run status after error for run %s", run_id)


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
    background_tasks.add_task(run_analysis_background, paper_id, run["id"], paper["file_path"], run.get("model_name"))
    return RunResponse(**run)
