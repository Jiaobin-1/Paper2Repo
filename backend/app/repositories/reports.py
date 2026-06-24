from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from app.repositories.connection import _json, get_connection, utc_now


def save_analysis_result(run_id: str, paper_id: str, payload: dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO analysis_results (
                id, run_id, paper_id, metadata_json, classification_json,
                understanding_json, method_json, experiments_json,
                reproduction_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                metadata_json = excluded.metadata_json,
                classification_json = excluded.classification_json,
                understanding_json = excluded.understanding_json,
                method_json = excluded.method_json,
                experiments_json = excluded.experiments_json,
                reproduction_json = excluded.reproduction_json
            """,
            (
                str(uuid.uuid4()),
                run_id,
                paper_id,
                _json(payload.get("metadata")),
                _json(payload.get("classification")),
                _json(payload.get("understanding")),
                _json(payload.get("method_analysis")),
                _json(payload.get("experiment_analysis")),
                _json(payload.get("reproduction_plan")),
                utc_now(),
            ),
        )


def get_analysis_result(run_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM analysis_results WHERE run_id = ?", (run_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    for key in [
        "metadata_json",
        "classification_json",
        "understanding_json",
        "method_json",
        "experiments_json",
        "reproduction_json",
    ]:
        result[key] = json.loads(result[key]) if result.get(key) else None
    return result


def save_report(run_id: str, paper_id: str, title: str, content: str, file_path: Path) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO reports (id, run_id, paper_id, title, content, file_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                title = excluded.title,
                content = excluded.content,
                file_path = excluded.file_path
            """,
            (str(uuid.uuid4()), run_id, paper_id, title, content, str(file_path), utc_now()),
        )


def get_report(run_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM reports WHERE run_id = ?", (run_id,)).fetchone()
    return dict(row) if row else None
