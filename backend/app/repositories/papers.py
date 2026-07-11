from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.repositories.connection import get_connection, utc_now


@dataclass(frozen=True)
class PaperDeletionResult:
    status: str
    paper: dict[str, Any] | None = None
    storage_paths: tuple[str, ...] = ()


def create_paper(
    filename: str,
    file_path: Path,
    file_size: int,
    title: str | None = None,
    arxiv_id: str | None = None,
) -> dict[str, Any]:
    paper_id = str(uuid.uuid4())
    created_at = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO papers (id, title, filename, file_path, file_size, created_at, arxiv_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (paper_id, title, filename, str(file_path), file_size, created_at, arxiv_id),
        )
    result = get_paper(paper_id)
    assert result is not None
    return result


def list_papers() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM papers ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def get_paper(paper_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    return dict(row) if row else None


def paper_has_active_runs(paper_id: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM analysis_runs
            WHERE paper_id = ?
              AND status IN ('pending', 'running')
            LIMIT 1
            """,
            (paper_id,),
        ).fetchone()
    return row is not None


def get_paper_storage_paths(paper_id: str) -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT file_path
            FROM papers
            WHERE id = ?
            UNION
            SELECT file_path
            FROM reports
            WHERE paper_id = ?
            """,
            (paper_id, paper_id),
        ).fetchall()
    return [row["file_path"] for row in rows if row["file_path"]]


def delete_paper(paper_id: str) -> PaperDeletionResult:
    with get_connection() as conn:
        # Serialize the active-run check and deletion so a concurrent run
        # cannot be created between the route precheck and destructive work.
        conn.execute("BEGIN IMMEDIATE")
        paper_row = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
        if paper_row is None:
            return PaperDeletionResult(status="not_found")
        paper = dict(paper_row)

        active_run = conn.execute(
            """
            SELECT 1
            FROM analysis_runs
            WHERE paper_id = ?
              AND status IN ('pending', 'running')
            LIMIT 1
            """,
            (paper_id,),
        ).fetchone()
        if active_run is not None:
            return PaperDeletionResult(status="active_runs", paper=paper)

        path_rows = conn.execute(
            """
            SELECT file_path FROM papers WHERE id = ?
            UNION
            SELECT file_path FROM reports WHERE paper_id = ?
            """,
            (paper_id, paper_id),
        ).fetchall()
        storage_paths = tuple(row["file_path"] for row in path_rows if row["file_path"])

        conn.execute("DELETE FROM analysis_jobs WHERE paper_id = ?", (paper_id,))
        conn.execute(
            """
            DELETE FROM llm_usage_events
            WHERE run_id IN (SELECT id FROM analysis_runs WHERE paper_id = ?)
            """,
            (paper_id,),
        )
        conn.execute("DELETE FROM qa_messages WHERE paper_id = ?", (paper_id,))
        conn.execute("DELETE FROM citations WHERE paper_id = ?", (paper_id,))
        conn.execute("DELETE FROM reports WHERE paper_id = ?", (paper_id,))
        conn.execute("DELETE FROM analysis_results WHERE paper_id = ?", (paper_id,))
        conn.execute("DELETE FROM analysis_runs WHERE paper_id = ?", (paper_id,))
        conn.execute("DELETE FROM paper_embeddings WHERE paper_id = ?", (paper_id,))
        conn.execute("DELETE FROM paper_chunks WHERE paper_id = ?", (paper_id,))
        conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
    return PaperDeletionResult(status="deleted", paper=paper, storage_paths=storage_paths)


def update_paper_title(paper_id: str, title: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE papers SET title = ? WHERE id = ?", (title, paper_id))
