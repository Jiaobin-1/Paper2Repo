from __future__ import annotations

import uuid
from typing import Any

from app.repositories.connection import get_connection


def create_citations(run_id: str, paper_id: str, citations: list[dict[str, Any]]) -> None:
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO citations (id, run_id, paper_id, citation_index, authors, title, venue, year, doi, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (str(uuid.uuid4()), run_id, paper_id, c["index"], c["authors"], c["title"], c.get("venue", ""), c.get("year", ""), c.get("doi", ""), c["raw_text"])
                for c in citations
            ],
        )


def get_citations_for_run(run_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM citations WHERE run_id = ? ORDER BY citation_index ASC",
            (run_id,),
        ).fetchall()
    return [dict(row) for row in rows]
