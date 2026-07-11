from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.repositories.connection import get_connection, utc_now
from app.repositories.settings import get_default_model

STALE_RUN_ERROR_MESSAGE = "任务中断或超时，请重新启动分析。"

def recover_stale_runs(conn: sqlite3.Connection | None = None) -> int:
    settings = get_settings()
    if settings.run_stale_after_minutes <= 0:
        return 0
    cutoff = (datetime.now(UTC) - timedelta(minutes=settings.run_stale_after_minutes)).isoformat()
    now = utc_now()

    def execute(connection: sqlite3.Connection) -> int:
        cursor = connection.execute(
            """
            UPDATE analysis_runs
            SET status = ?,
                error_message = ?,
                current_step = ?,
                progress_percent = CASE WHEN progress_percent >= 100 THEN 99 ELSE progress_percent END,
                completed_at = COALESCE(completed_at, ?),
                updated_at = ?
            WHERE status IN ('pending', 'running')
              AND COALESCE(updated_at, started_at, created_at) < ?
              AND NOT EXISTS (
                  SELECT 1
                  FROM analysis_jobs j
                  WHERE j.run_id = analysis_runs.id
                    AND j.cancel_requested = 0
                    AND j.status IN ('pending', 'running')
                    AND j.attempts < j.max_attempts
              )
            """,
            ("failed", STALE_RUN_ERROR_MESSAGE, "failed", now, now, cutoff),
        )
        return cursor.rowcount

    if conn is not None:
        return execute(conn)
    with get_connection() as local_conn:
        return execute(local_conn)


def create_run(paper_id: str, model_name: str | None = None, batch_id: str | None = None) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    now = utc_now()
    selected_model = model_name or get_default_model()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, paper_id, status, model_name, current_step, progress_percent,
                started_at, created_at, updated_at, batch_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, paper_id, "pending", selected_model, "queued", 0, now, now, now, batch_id),
        )
    result = get_run(run_id)
    assert result is not None
    return result


def update_run_status(
    run_id: str,
    status: str,
    error_message: str | None = None,
    completed: bool = False,
    current_step: str | None = None,
    progress_percent: int | None = None,
) -> None:
    completed_at = utc_now() if completed else None
    updated_at = utc_now()
    if progress_percent is not None:
        progress_percent = max(0, min(100, progress_percent))
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE analysis_runs
            SET status = ?,
                error_message = ?,
                current_step = COALESCE(?, current_step),
                progress_percent = COALESCE(?, progress_percent),
                completed_at = COALESCE(?, completed_at),
                updated_at = ?
            WHERE id = ?
            """,
            (status, error_message, current_step, progress_percent, completed_at, updated_at, run_id),
        )


def get_run(run_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
    return _normalize_run_record(dict(row)) if row else None


def list_runs(paper_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    bounded_limit = max(1, min(limit, 100))
    query = """
        SELECT
            r.*,
            p.title AS paper_title,
            p.filename AS paper_filename
        FROM analysis_runs r
        JOIN papers p ON p.id = r.paper_id
    """
    params: list[Any] = []
    if paper_id:
        query += " WHERE r.paper_id = ?"
        params.append(paper_id)
    query += " ORDER BY r.created_at DESC LIMIT ?"
    params.append(bounded_limit)
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_normalize_run_record(dict(row)) for row in rows]


def delete_run(run_id: str) -> dict[str, Any] | None:
    run = get_run(run_id)
    if not run:
        return None
    with get_connection() as conn:
        conn.execute("DELETE FROM analysis_jobs WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM llm_usage_events WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM qa_messages WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM citations WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM reports WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM analysis_results WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM analysis_runs WHERE id = ?", (run_id,))
    return run


def create_batch_id() -> str:
    return str(uuid.uuid4())


def get_runs_by_batch(batch_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT r.*, p.title AS paper_title, p.filename AS paper_filename
            FROM analysis_runs r
            JOIN papers p ON p.id = r.paper_id
            WHERE r.batch_id = ?
            ORDER BY r.created_at ASC
            """,
            (batch_id,),
        ).fetchall()
    return [_normalize_run_record(dict(row)) for row in rows]


def _normalize_run_record(run: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(run)
    if normalized.get("status") == "completed":
        normalized["current_step"] = "completed"
        normalized["progress_percent"] = 100
        if not normalized.get("completed_at"):
            normalized["completed_at"] = normalized.get("updated_at") or normalized.get("started_at") or normalized.get("created_at")
    return normalized
