from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.agents.graph import run_analysis
from app.core.config import get_settings
from app.core.database import (
    create_paper,
    create_run,
    get_paper,
    get_run,
    list_papers,
    update_run_status,
)
from app.schemas.paper import PaperResponse, RunResponse

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("/upload", response_model=PaperResponse)
def upload_paper(file: UploadFile = File(...)) -> PaperResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    settings = get_settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    stored_name = f"{uuid.uuid4()}_{safe_name}"
    file_path = settings.upload_path / stored_name

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    paper = create_paper(filename=safe_name, file_path=file_path, file_size=file_path.stat().st_size)
    return PaperResponse(**paper)


@router.get("", response_model=list[PaperResponse])
def get_papers() -> list[PaperResponse]:
    return [PaperResponse(**paper) for paper in list_papers()]


@router.get("/{paper_id}", response_model=PaperResponse)
def get_paper_detail(paper_id: str) -> PaperResponse:
    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return PaperResponse(**paper)


@router.post("/{paper_id}/runs", response_model=RunResponse)
def start_run(paper_id: str) -> RunResponse:
    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    run = create_run(paper_id)
    run_id = run["id"]
    try:
        update_run_status(run_id, "running")
        run_analysis(paper_id=paper_id, run_id=run_id, pdf_path=paper["file_path"])
        update_run_status(run_id, "completed", completed=True)
    except Exception as exc:
        update_run_status(run_id, "failed", error_message=str(exc), completed=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    completed_run = get_run(run_id)
    return RunResponse(**completed_run)
