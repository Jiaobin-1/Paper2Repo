from __future__ import annotations

import time
from contextlib import suppress
from pathlib import Path

from app.core.config import get_settings
from app.repositories.connection import get_connection
from app.schemas.storage import (
    StorageAreaSummary,
    StorageCleanupCandidate,
    StorageCleanupResponse,
    StorageSummaryResponse,
)

MAX_CANDIDATES_IN_RESPONSE = 100


def get_storage_summary() -> StorageSummaryResponse:
    settings = get_settings()
    uploads = _summarize_area(settings.upload_path)
    reports = _summarize_area(settings.report_path)
    database = _summarize_file(settings.database_path)
    candidates = find_cleanup_candidates()
    orphan_bytes = sum(candidate.byte_count for candidate in candidates)
    return StorageSummaryResponse(
        uploads=uploads,
        reports=reports,
        database=database,
        total_bytes=uploads.byte_count + reports.byte_count + database.byte_count,
        orphan_file_count=len(candidates),
        orphan_bytes=orphan_bytes,
        cleanup_min_age_hours=max(0, settings.storage_cleanup_min_age_hours),
        cleanup_candidates=candidates[:MAX_CANDIDATES_IN_RESPONSE],
    )


def cleanup_orphan_storage(*, dry_run: bool = True) -> StorageCleanupResponse:
    candidates = find_cleanup_candidates()
    deleted_count = 0
    deleted_bytes = 0
    skipped_count = 0

    if not dry_run:
        settings = get_settings()
        managed_roots = {
            "uploads": settings.upload_path,
            "reports": settings.report_path,
        }
        for candidate in candidates:
            path = Path(candidate.path)
            managed_root = managed_roots.get(candidate.area)
            if managed_root is None or path.is_symlink() or not _is_inside(path, managed_root):
                skipped_count += 1
                continue
            try:
                path.unlink()
            except OSError:
                skipped_count += 1
                continue
            deleted_count += 1
            deleted_bytes += candidate.byte_count

    return StorageCleanupResponse(
        dry_run=dry_run,
        deleted_file_count=deleted_count,
        deleted_bytes=deleted_bytes,
        skipped_file_count=skipped_count,
        candidates=candidates[:MAX_CANDIDATES_IN_RESPONSE],
    )


def delete_managed_file(path_value: str | Path | None, *, area: str = "reports") -> bool:
    if not path_value:
        return False
    settings = get_settings()
    allowed_root = settings.report_path if area == "reports" else settings.upload_path
    path = Path(path_value)
    if not _is_inside(path, allowed_root):
        return False
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return False
    return True


def cleanup_temp_file(path_value: str | Path) -> None:
    path = Path(path_value)
    try:
        path.unlink(missing_ok=True)
    finally:
        with suppress(OSError):
            path.parent.rmdir()


def find_cleanup_candidates() -> list[StorageCleanupCandidate]:
    settings = get_settings()
    min_age_seconds = max(0, settings.storage_cleanup_min_age_hours) * 3600
    registered_uploads, registered_reports = _registered_storage_paths()
    now = time.time()
    candidates: list[StorageCleanupCandidate] = []

    candidates.extend(
        _orphan_candidates(
            area="uploads",
            root=settings.upload_path,
            registered=registered_uploads,
            min_age_seconds=min_age_seconds,
            now=now,
        )
    )
    candidates.extend(
        _orphan_candidates(
            area="reports",
            root=settings.report_path,
            registered=registered_reports,
            min_age_seconds=min_age_seconds,
            now=now,
        )
    )
    candidates.sort(key=lambda candidate: (candidate.area, candidate.path))
    return candidates


def _registered_storage_paths() -> tuple[set[Path], set[Path]]:
    with get_connection() as conn:
        upload_rows = conn.execute("SELECT file_path FROM papers").fetchall()
        report_rows = conn.execute("SELECT file_path FROM reports").fetchall()
    uploads = {_safe_resolve(row["file_path"]) for row in upload_rows if row["file_path"]}
    reports = {_safe_resolve(row["file_path"]) for row in report_rows if row["file_path"]}
    return uploads, reports


def _orphan_candidates(
    *,
    area: str,
    root: Path,
    registered: set[Path],
    min_age_seconds: int,
    now: float,
) -> list[StorageCleanupCandidate]:
    candidates: list[StorageCleanupCandidate] = []
    for path in _iter_files(root):
        resolved = _safe_resolve(path)
        if not _is_inside(path, root):
            continue
        if resolved in registered:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        age_seconds = max(0.0, now - stat.st_mtime)
        if age_seconds < min_age_seconds:
            continue
        candidates.append(
            StorageCleanupCandidate(
                area=area,
                path=str(path.absolute()),
                byte_count=stat.st_size,
                age_hours=round(age_seconds / 3600, 2),
                reason="not referenced by the database",
            )
        )
    return candidates


def _summarize_area(root: Path) -> StorageAreaSummary:
    files = list(_iter_files(root))
    byte_count = 0
    for path in files:
        try:
            byte_count += path.stat().st_size
        except OSError:
            continue
    return StorageAreaSummary(path=str(root), file_count=len(files), byte_count=byte_count)


def _summarize_file(path: Path) -> StorageAreaSummary:
    try:
        size = path.stat().st_size
        count = 1
    except OSError:
        size = 0
        count = 0
    return StorageAreaSummary(path=str(path), file_count=count, byte_count=size)


def _iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [path for path in root.rglob("*") if not path.is_symlink() and path.is_file()]


def _safe_resolve(path_value: str | Path) -> Path:
    return Path(path_value).expanduser().resolve()


def _is_inside(path: Path, root: Path) -> bool:
    try:
        _safe_resolve(path).relative_to(_safe_resolve(root))
    except ValueError:
        return False
    return True
