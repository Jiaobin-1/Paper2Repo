from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.repositories.connection import get_connection, utc_now


def create_analysis_job(run_id: str, paper_id: str, max_attempts: int | None = None) -> dict[str, Any]:
    settings = get_settings()
    now = utc_now()
    attempts_limit = max(1, max_attempts or settings.analysis_job_max_attempts)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO analysis_jobs (
                id, run_id, paper_id, status, attempts, max_attempts,
                lease_until, cancel_requested, error_message, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status = CASE
                    WHEN analysis_jobs.status IN ('completed', 'canceled') THEN analysis_jobs.status
                    ELSE excluded.status
                END,
                max_attempts = excluded.max_attempts,
                updated_at = excluded.updated_at
            """,
            (str(uuid.uuid4()), run_id, paper_id, "pending", 0, attempts_limit, None, 0, None, now, now),
        )
    job = get_analysis_job(run_id)
    assert job is not None
    return job


def get_analysis_job(run_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM analysis_jobs WHERE run_id = ?", (run_id,)).fetchone()
    return dict(row) if row else None


def claim_analysis_job(run_id: str) -> str:
    """Return claimed, busy, missing, completed, or canceled."""
    settings = get_settings()
    lease_until = (datetime.now(UTC) + timedelta(seconds=max(60, settings.analysis_job_lease_seconds))).isoformat()
    now = utc_now()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM analysis_jobs WHERE run_id = ?", (run_id,)).fetchone()
        if not row:
            return "missing"
        if row["status"] == "completed":
            return "completed"
        if row["cancel_requested"]:
            conn.execute(
                """
                UPDATE analysis_jobs
                SET status = ?, updated_at = ?
                WHERE run_id = ?
                """,
                ("canceled", now, run_id),
            )
            return "canceled"
        cursor = conn.execute(
            """
            UPDATE analysis_jobs
            SET status = ?, attempts = attempts + 1, lease_until = ?, error_message = NULL, updated_at = ?
            WHERE run_id = ?
              AND cancel_requested = 0
              AND status IN ('pending', 'running')
              AND (status = 'pending' OR lease_until IS NULL OR lease_until < ?)
            """,
            ("running", lease_until, now, run_id, now),
        )
    return "claimed" if cursor.rowcount > 0 else "busy"


def renew_analysis_job_lease(run_id: str) -> bool:
    settings = get_settings()
    lease_until = (datetime.now(UTC) + timedelta(seconds=max(60, settings.analysis_job_lease_seconds))).isoformat()
    now = utc_now()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE analysis_jobs
            SET lease_until = ?, updated_at = ?
            WHERE run_id = ? AND status = 'running' AND cancel_requested = 0
            """,
            (lease_until, now, run_id),
        )
    return cursor.rowcount > 0


def complete_analysis_job(run_id: str) -> None:
    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE analysis_jobs
            SET status = ?, lease_until = NULL, error_message = NULL, updated_at = ?
            WHERE run_id = ?
            """,
            ("completed", now, run_id),
        )


def fail_analysis_job(run_id: str, error_message: str) -> str:
    now = utc_now()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT attempts, max_attempts, cancel_requested FROM analysis_jobs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if not row:
            return "missing"
        if row["cancel_requested"]:
            status = "canceled"
        elif row["attempts"] < row["max_attempts"]:
            status = "pending"
        else:
            status = "failed"
        conn.execute(
            """
            UPDATE analysis_jobs
            SET status = ?, lease_until = NULL, error_message = ?, updated_at = ?
            WHERE run_id = ?
            """,
            (status, error_message, now, run_id),
        )
    return status


def request_analysis_cancel(run_id: str) -> bool:
    now = utc_now()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE analysis_jobs
            SET cancel_requested = 1, updated_at = ?
            WHERE run_id = ? AND status IN ('pending', 'running')
            """,
            (now, run_id),
        )
    return cursor.rowcount > 0


def is_analysis_cancel_requested(run_id: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT cancel_requested FROM analysis_jobs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    return bool(row and row["cancel_requested"])


def list_recoverable_analysis_jobs(limit: int = 20) -> list[dict[str, Any]]:
    bounded_limit = max(1, min(limit, 100))
    now = utc_now()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT j.*, r.status AS run_status
            FROM analysis_jobs j
            JOIN analysis_runs r ON r.id = j.run_id
            WHERE j.cancel_requested = 0
              AND j.status IN ('pending', 'running')
              AND r.status IN ('pending', 'running')
              AND (j.status = 'pending' OR j.lease_until IS NULL OR j.lease_until < ?)
            ORDER BY j.created_at ASC
            LIMIT ?
            """,
            (now, bounded_limit),
        ).fetchall()
    return [dict(row) for row in rows]
