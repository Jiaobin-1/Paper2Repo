from __future__ import annotations

import uuid
from typing import Any

from app.repositories.connection import _json, get_connection, utc_now


def replace_chunks(paper_id: str, chunks: list[dict[str, Any]]) -> None:
    now = utc_now()
    with get_connection() as conn:
        conn.execute("DELETE FROM paper_chunks WHERE paper_id = ?", (paper_id,))
        conn.executemany(
            """
            INSERT INTO paper_chunks (
                id, paper_id, chunk_index, page_start, page_end,
                section_title, content, metadata_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    str(uuid.uuid4()),
                    paper_id,
                    chunk["metadata"]["chunk_index"],
                    chunk["metadata"]["page_start"],
                    chunk["metadata"]["page_end"],
                    chunk["metadata"].get("section_title"),
                    chunk["content"],
                    _json(chunk["metadata"]),
                    now,
                )
                for chunk in chunks
            ],
        )


def get_paper_chunks(paper_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM paper_chunks WHERE paper_id = ? ORDER BY chunk_index ASC",
            (paper_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def save_embeddings(paper_id: str, embeddings: list[tuple[int, bytes]]) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM paper_embeddings WHERE paper_id = ?", (paper_id,))
        conn.executemany(
            "INSERT INTO paper_embeddings (id, paper_id, chunk_index, embedding) VALUES (?, ?, ?, ?)",
            [(str(uuid.uuid4()), paper_id, idx, emb) for idx, emb in embeddings],
        )


def get_all_embeddings() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT pe.paper_id, pe.chunk_index, pe.embedding,
                   pc.content, pc.section_title, pc.page_start, pc.page_end,
                   p.title AS paper_title
            FROM paper_embeddings pe
            JOIN paper_chunks pc ON pe.paper_id = pc.paper_id AND pe.chunk_index = pc.chunk_index
            JOIN papers p ON pe.paper_id = p.id
            ORDER BY pe.paper_id, pe.chunk_index
            """
        ).fetchall()
    return [dict(row) for row in rows]


def delete_embeddings(paper_id: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM paper_embeddings WHERE paper_id = ?", (paper_id,))
