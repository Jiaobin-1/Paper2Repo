from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.core.config import get_settings

DEFAULT_MODEL_SETTING_KEY = "default_model"
UI_LANGUAGE_SETTING_KEY = "ui_language"
REPORT_LANGUAGE_SETTING_KEY = "report_language"
THEME_SETTING_KEY = "theme"
SUPPORTED_LANGUAGES = {"zh", "en"}
SUPPORTED_THEMES = {"light", "dark", "system"}
STALE_RUN_ERROR_MESSAGE = "任务中断或超时，请重新启动分析。"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


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
                updated_at TEXT NOT NULL,
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

            CREATE TABLE IF NOT EXISTS qa_messages (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                paper_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(id),
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            );

            CREATE TABLE IF NOT EXISTS paper_embeddings (
                id TEXT PRIMARY KEY,
                paper_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                embedding BLOB NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            );

            CREATE TABLE IF NOT EXISTS citations (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                paper_id TEXT NOT NULL,
                citation_index INTEGER NOT NULL,
                authors TEXT NOT NULL,
                title TEXT NOT NULL,
                venue TEXT NOT NULL DEFAULT '',
                year TEXT NOT NULL DEFAULT '',
                doi TEXT NOT NULL DEFAULT '',
                raw_text TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(id),
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            );

            CREATE TABLE IF NOT EXISTS analysis_jobs (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL UNIQUE,
                paper_id TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 2,
                lease_until TEXT,
                cancel_requested INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(id),
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            );
            """
        )
        _ensure_analysis_run_columns(conn)
        _ensure_batch_column(conn)
        _ensure_default_model_setting(conn)
        _ensure_language_settings(conn)
        _ensure_paper_columns(conn)
        _repair_completed_runs(conn)
        recover_stale_runs(conn)


def _ensure_analysis_run_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(analysis_runs)").fetchall()}
    if "model_name" not in columns:
        conn.execute("ALTER TABLE analysis_runs ADD COLUMN model_name TEXT")
    if "current_step" not in columns:
        conn.execute("ALTER TABLE analysis_runs ADD COLUMN current_step TEXT")
    if "progress_percent" not in columns:
        conn.execute("ALTER TABLE analysis_runs ADD COLUMN progress_percent INTEGER NOT NULL DEFAULT 0")
    if "updated_at" not in columns:
        conn.execute("ALTER TABLE analysis_runs ADD COLUMN updated_at TEXT")
    conn.execute(
        """
        UPDATE analysis_runs
        SET updated_at = COALESCE(updated_at, completed_at, started_at, created_at, ?)
        WHERE updated_at IS NULL OR updated_at = ''
        """,
        (utc_now(),),
    )


def _repair_completed_runs(conn: sqlite3.Connection) -> None:
    now = utc_now()
    conn.execute(
        """
        UPDATE analysis_runs
        SET current_step = 'completed',
            progress_percent = 100,
            completed_at = COALESCE(completed_at, updated_at, started_at, created_at, ?),
            updated_at = COALESCE(NULLIF(updated_at, ''), completed_at, started_at, created_at, ?)
        WHERE status = 'completed'
          AND (
              current_step IS NULL
              OR current_step != 'completed'
              OR progress_percent != 100
              OR completed_at IS NULL
          )
        """,
        (now, now),
    )


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
            """,
            ("failed", STALE_RUN_ERROR_MESSAGE, "failed", now, now, cutoff),
        )
        return cursor.rowcount

    if conn is not None:
        return execute(conn)
    with get_connection() as local_conn:
        return execute(local_conn)


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


def _ensure_language_settings(conn: sqlite3.Connection) -> None:
    _ensure_setting(conn, UI_LANGUAGE_SETTING_KEY, "zh", SUPPORTED_LANGUAGES)
    _ensure_setting(conn, REPORT_LANGUAGE_SETTING_KEY, "en", SUPPORTED_LANGUAGES)
    _ensure_setting(conn, THEME_SETTING_KEY, "light", SUPPORTED_THEMES)


def _ensure_paper_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(papers)").fetchall()}
    if "arxiv_id" not in columns:
        conn.execute("ALTER TABLE papers ADD COLUMN arxiv_id TEXT")


def _ensure_setting(conn: sqlite3.Connection, key: str, default_value: str, allowed_values: set[str]) -> None:
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key = ?",
        (key,),
    ).fetchone()
    if row and row["value"] in allowed_values:
        return
    conn.execute(
        """
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
        """,
        (key, default_value, utc_now()),
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


def get_ui_language() -> str:
    return _get_language_setting(UI_LANGUAGE_SETTING_KEY, "zh")


def set_ui_language(language: str) -> str:
    return _set_language_setting(UI_LANGUAGE_SETTING_KEY, language)


def get_report_language() -> str:
    return _get_language_setting(REPORT_LANGUAGE_SETTING_KEY, "en")


def set_report_language(language: str) -> str:
    return _set_language_setting(REPORT_LANGUAGE_SETTING_KEY, language)


def _get_language_setting(key: str, default_value: str) -> str:
    stored_language = get_app_setting(key)
    if stored_language in SUPPORTED_LANGUAGES:
        return stored_language
    set_app_setting(key, default_value)
    return default_value


def _set_language_setting(key: str, language: str) -> str:
    normalized_language = language.strip().lower()
    if normalized_language not in SUPPORTED_LANGUAGES:
        raise ValueError("Language must be zh or en.")
    set_app_setting(key, normalized_language)
    return normalized_language


def get_theme() -> str:
    stored_theme = get_app_setting(THEME_SETTING_KEY)
    if stored_theme in SUPPORTED_THEMES:
        return stored_theme
    set_app_setting(THEME_SETTING_KEY, "light")
    return "light"


def set_theme(theme: str) -> str:
    normalized_theme = theme.strip().lower()
    if normalized_theme not in SUPPORTED_THEMES:
        raise ValueError("Theme must be light, dark, or system.")
    set_app_setting(THEME_SETTING_KEY, normalized_theme)
    return normalized_theme


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
    """Return claimed, missing, completed, or canceled."""
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
        conn.execute(
            """
            UPDATE analysis_jobs
            SET status = ?, attempts = attempts + 1, lease_until = ?, error_message = NULL, updated_at = ?
            WHERE run_id = ?
            """,
            ("running", lease_until, now, run_id),
        )
    return "claimed"


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


def delete_run(run_id: str) -> dict[str, Any] | None:
    run = get_run(run_id)
    if not run:
        return None
    with get_connection() as conn:
        conn.execute("DELETE FROM analysis_jobs WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM qa_messages WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM reports WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM analysis_results WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM analysis_runs WHERE id = ?", (run_id,))
    return run


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


def _ensure_batch_column(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(analysis_runs)").fetchall()}
    if "batch_id" not in columns:
        conn.execute("ALTER TABLE analysis_runs ADD COLUMN batch_id TEXT")


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
