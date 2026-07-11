from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.core.database import init_db
from app.schemas.storage import StorageCleanupCandidate
from app.services import storage_maintenance


@pytest.fixture()
def storage_settings(isolated_settings: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("STORAGE_CLEANUP_MIN_AGE_HOURS", "0")
    get_settings.cache_clear()
    init_db()
    yield get_settings()
    get_settings.cache_clear()


def test_cleanup_deletes_regular_orphan(storage_settings) -> None:
    orphan = storage_settings.upload_path / "orphan.pdf"
    orphan.write_bytes(b"orphan")

    response = storage_maintenance.cleanup_orphan_storage(dry_run=False)

    assert response.deleted_file_count == 1
    assert response.deleted_bytes == len(b"orphan")
    assert not orphan.exists()


def test_cleanup_does_not_follow_symlinks_outside_managed_storage(storage_settings, tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("keep", encoding="utf-8")
    link = storage_settings.upload_path / "outside-link"
    try:
        link.symlink_to(outside)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")

    candidates = storage_maintenance.find_cleanup_candidates()
    response = storage_maintenance.cleanup_orphan_storage(dry_run=False)

    assert all(Path(candidate.path) != outside for candidate in candidates)
    assert response.deleted_file_count == 0
    assert outside.read_text(encoding="utf-8") == "keep"
    assert link.is_symlink()


def test_cleanup_revalidates_candidate_before_deleting(
    storage_settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("keep", encoding="utf-8")
    candidate = StorageCleanupCandidate(
        area="uploads",
        path=os.fspath(outside),
        byte_count=outside.stat().st_size,
        age_hours=24,
        reason="test candidate",
    )
    monkeypatch.setattr(storage_maintenance, "find_cleanup_candidates", lambda: [candidate])

    response = storage_maintenance.cleanup_orphan_storage(dry_run=False)

    assert response.deleted_file_count == 0
    assert response.skipped_file_count == 1
    assert outside.read_text(encoding="utf-8") == "keep"
