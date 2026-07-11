from __future__ import annotations

import uuid
from typing import Any

from app.repositories.connection import get_connection, utc_now


def save_qa_message(run_id: str, paper_id: str, role: str, content: str) -> dict[str, Any]:
    message_id = str(uuid.uuid4())
    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO qa_messages (id, run_id, paper_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (message_id, run_id, paper_id, role, content, now),
        )
    return {"id": message_id, "run_id": run_id, "paper_id": paper_id, "role": role, "content": content, "created_at": now}


def get_qa_history(run_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM qa_messages WHERE run_id = ? ORDER BY created_at ASC",
            (run_id,),
        ).fetchall()
    return [dict(row) for row in rows]
