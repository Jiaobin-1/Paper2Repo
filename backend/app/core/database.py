from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings

DEFAULT_MODEL_SETTING_KEY = "default_model"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def get_connection() -> sqlite3.Connection:
    settings = get_settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.database_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db() -> None:
    settings = get_settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.report_path.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                title TEXT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS paper_chunks (
                id TEXT PRIMARY KEY,
                paper_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                page_start INTEGER NOT NULL,
                page_end INTEGER NOT NULL,
                section_title TEXT,
                content TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            );

            CREATE TABLE IF NOT EXISTS analysis_runs (
                id TEXT PRIMARY KEY,
                paper_id TEXT NOT NULL,
                status TEXT NOT NULL,
                model_name TEXT,
                current_step TEXT,
                progress_percent INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                started_at TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            );

            CREATE TABLE IF NOT EXISTS analysis_results (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL UNIQUE,
                paper_id TEXT NOT NULL,
                metadata_json TEXT,
                classification_json TEXT,
                understanding_json TEXT,
                method_json TEXT,
                experiments_json TEXT,
                reproduction_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(id),
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            );

            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL UNIQUE,
                paper_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(id),
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        _ensure_analysis_run_columns(conn)
        _ensure_default_model_setting(conn)


def _ensure_analysis_run_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(analysis_runs)").fetchall()}
    if "model_name" not in columns:
        conn.execute("ALTER TABLE analysis_runs ADD COLUMN model_name TEXT")
    if "current_step" not in columns:
        conn.execute("ALTER TABLE analysis_runs ADD COLUMN current_step TEXT")
    if "progress_percent" not in columns:
        conn.execute("ALTER TABLE analysis_runs ADD COLUMN progress_percent INTEGER NOT NULL DEFAULT 0")


def _ensure_default_model_setting(conn: sqlite3.Connection) -> None:
    settings = get_settings()
    available_models = settings.available_openai_models
    configured_default = settings.openai_model.strip() or available_models[0]
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key = ?",
        (DEFAULT_MODEL_SETTING_KEY,),
    ).fetchone()
    if row and row["value"] in available_models:
        return
    conn.execute(
        """
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
        """,
        (DEFAULT_MODEL_SETTING_KEY, configured_default, utc_now()),
    )


def get_app_setting(key: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_app_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, utc_now()),
        )


def get_default_model() -> str:
    settings = get_settings()
    available_models = settings.available_openai_models
    stored_model = get_app_setting(DEFAULT_MODEL_SETTING_KEY)
    if stored_model in available_models:
        return stored_model
    default_model = settings.openai_model.strip() or available_models[0]
    set_app_setting(DEFAULT_MODEL_SETTING_KEY, default_model)
    return default_model


def set_default_model(model_name: str) -> str:
    normalized_model = model_name.strip()
    if normalized_model not in get_settings().available_openai_models:
        raise ValueError("Model is not listed in OPENAI_MODEL_OPTIONS.")
    set_app_setting(DEFAULT_MODEL_SETTING_KEY, normalized_model)
    return normalized_model


def create_paper(filename: str, file_path: Path, file_size: int, title: str | None = None) -> dict[str, Any]:
    paper_id = str(uuid.uuid4())
    created_at = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO papers (id, title, filename, file_path, file_size, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (paper_id, title, filename, str(file_path), file_size, created_at),
        )
    return get_paper(paper_id)


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


def create_run(paper_id: str, model_name: str | None = None) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    now = utc_now()
    selected_model = model_name or get_default_model()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, paper_id, status, model_name, current_step, progress_percent,
                started_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, paper_id, "pending", selected_model, "queued", 0, now, now),
        )
    return get_run(run_id)


def update_run_status(
    run_id: str,
    status: str,
    error_message: str | None = None,
    completed: bool = False,
    current_step: str | None = None,
    progress_percent: int | None = None,
) -> None:
    completed_at = utc_now() if completed else None
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
                completed_at = COALESCE(?, completed_at)
            WHERE id = ?
            """,
            (status, error_message, current_step, progress_percent, completed_at, run_id),
        )


def get_run(run_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
    return dict(row) if row else None


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
    return [dict(row) for row in rows]


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
