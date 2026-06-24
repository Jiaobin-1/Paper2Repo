from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from app.repositories.connection import get_connection, utc_now


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


def update_paper_title(paper_id: str, title: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE papers SET title = ? WHERE id = ?", (title, paper_id))
