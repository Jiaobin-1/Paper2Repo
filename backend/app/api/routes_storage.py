from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.storage import StorageCleanupResponse, StorageSummaryResponse
from app.services.storage_maintenance import cleanup_orphan_storage, get_storage_summary

router = APIRouter(
    prefix="/storage",
    tags=["storage"],
)


@router.get(
    "/summary",
    response_model=StorageSummaryResponse,
    summary="Get storage summary",
    description="Return upload, report, database, and orphan-file storage statistics.",
)
def get_storage_summary_route() -> StorageSummaryResponse:
    return get_storage_summary()


@router.post(
    "/cleanup",
    response_model=StorageCleanupResponse,
    summary="Clean orphan storage files",
    description="Delete files under managed storage directories that are no longer referenced by the database.",
)
def cleanup_storage_route(
    dry_run: bool = Query(True, description="Preview cleanup candidates without deleting files."),
) -> StorageCleanupResponse:
    return cleanup_orphan_storage(dry_run=dry_run)
