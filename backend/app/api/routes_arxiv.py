from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.database import create_analysis_job, create_paper, create_run, delete_run, update_paper_title
from app.schemas.paper import PaperResponse
from app.services import analysis_runner
from app.services.arxiv_client import (
    download_arxiv_pdf,
    fetch_arxiv_metadata,
    get_arxiv_versions,
    normalize_arxiv_id,
)

router = APIRouter(
    prefix="/arxiv",
    tags=["arxiv"],
)


class ArxivImportRequest(BaseModel):
    arxiv_id: str


class ArxivVersionResponse(BaseModel):
    versions: list[dict[str, str]]


@router.post(
    "/import",
    response_model=PaperResponse,
    summary="Import paper from arXiv",
    description="Download a paper from arXiv by ID, create a paper record, and trigger analysis.",
)
def import_arxiv(
    payload: ArxivImportRequest,
) -> PaperResponse:
    arxiv_id = normalize_arxiv_id(payload.arxiv_id)
    if not arxiv_id:
        raise HTTPException(status_code=400, detail="Invalid arXiv ID or URL.")

    settings = get_settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)

    try:
        pdf_path = download_arxiv_pdf(arxiv_id, settings.upload_path, max_bytes=settings.upload_max_bytes)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Failed to download a valid PDF from arXiv.") from exc

    file_size = pdf_path.stat().st_size
    metadata = fetch_arxiv_metadata(arxiv_id)
    title = metadata.get("title") if metadata else None

    paper = create_paper(
        filename=pdf_path.name,
        file_path=pdf_path,
        file_size=file_size,
        title=title,
        arxiv_id=arxiv_id,
    )

    if title:
        update_paper_title(paper["id"], title)

    run = create_run(paper["id"])
    create_analysis_job(run["id"], paper["id"])
    try:
        analysis_runner.submit_analysis(paper["id"], run["id"], str(pdf_path), run.get("model_name"))
    except analysis_runner.AnalysisQueueFullError as exc:
        delete_run(run["id"])
        raise HTTPException(status_code=503, detail=str(exc), headers={"Retry-After": "5"}) from exc

    return PaperResponse(**paper)


@router.get(
    "/{arxiv_id}/versions",
    summary="Get arXiv versions",
    description="Retrieve available versions of an arXiv paper.",
)
def get_versions(arxiv_id: str) -> dict[str, Any]:
    arxiv_id = normalize_arxiv_id(arxiv_id)
    if not arxiv_id:
        raise HTTPException(status_code=400, detail="Invalid arXiv ID.")

    versions = get_arxiv_versions(arxiv_id)
    metadata = fetch_arxiv_metadata(arxiv_id)

    return {
        "arxiv_id": arxiv_id,
        "title": metadata.get("title", ""),
        "versions": versions,
    }


@router.post(
    "/compare",
    summary="Compare arXiv paper versions",
    description="Download two versions of the same arXiv paper and return their analysis results for comparison.",
)
def compare_versions(
    arxiv_id: str,
    version_a: str,
    version_b: str,
) -> dict[str, Any]:
    base_id = normalize_arxiv_id(arxiv_id)
    if not base_id:
        raise HTTPException(status_code=400, detail="Invalid arXiv ID.")
    base_id = re.sub(r"v\d+$", "", base_id)
    if not re.fullmatch(r"v\d+", version_a) or not re.fullmatch(r"v\d+", version_b):
        raise HTTPException(status_code=400, detail="Versions must use the form v1, v2, and so on.")

    id_a = f"{base_id}{version_a}" if not base_id.endswith(version_a) else base_id
    id_b = f"{base_id}{version_b}" if not base_id.endswith(version_b) else base_id

    settings = get_settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)

    results = {}
    for label, vid in [("version_a", id_a), ("version_b", id_b)]:
        try:
            pdf_path = download_arxiv_pdf(vid, settings.upload_path, max_bytes=settings.upload_max_bytes)
            metadata = fetch_arxiv_metadata(vid)
            paper = create_paper(
                filename=pdf_path.name,
                file_path=pdf_path,
                file_size=pdf_path.stat().st_size,
                title=metadata.get("title"),
                arxiv_id=vid,
            )
            run = create_run(paper["id"])
            create_analysis_job(run["id"], paper["id"])
            try:
                analysis_runner.submit_analysis(paper["id"], run["id"], str(pdf_path), run.get("model_name"))
            except analysis_runner.AnalysisQueueFullError:
                delete_run(run["id"])
                raise
            results[label] = {
                "paper_id": paper["id"],
                "run_id": run["id"],
                "arxiv_id": vid,
                "status": "analysis_started",
            }
        except Exception:
            results[label] = {"error": "Failed to download or start analysis for this arXiv version."}

    return results
