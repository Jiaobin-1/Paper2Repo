from __future__ import annotations

import sqlite3

from app.core.config import get_settings
from app.repositories.connection import get_connection, utc_now
from app.repositories.runs import recover_stale_runs
from app.repositories.settings import _ensure_default_model_setting, _ensure_language_settings


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

            CREATE TABLE IF NOT EXISTS llm_usage_events (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                model TEXT NOT NULL,
                mode TEXT NOT NULL,
                operation TEXT NOT NULL,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                estimated_cost_usd REAL NOT NULL DEFAULT 0,
                latency_ms REAL NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(id)
            );
            """
        )
        _ensure_analysis_run_columns(conn)
        _ensure_batch_column(conn)
        _ensure_default_model_setting(conn)
        _ensure_language_settings(conn)
        _ensure_paper_columns(conn)
        _ensure_indexes(conn)
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


def _ensure_paper_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(papers)").fetchall()}
    if "arxiv_id" not in columns:
        conn.execute("ALTER TABLE papers ADD COLUMN arxiv_id TEXT")


def _ensure_batch_column(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(analysis_runs)").fetchall()}
    if "batch_id" not in columns:
        conn.execute("ALTER TABLE analysis_runs ADD COLUMN batch_id TEXT")


def _ensure_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_papers_created_at
            ON papers(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_paper_chunks_paper_chunk
            ON paper_chunks(paper_id, chunk_index);
        CREATE INDEX IF NOT EXISTS idx_paper_embeddings_paper_chunk
            ON paper_embeddings(paper_id, chunk_index);
        CREATE INDEX IF NOT EXISTS idx_analysis_runs_paper_created
            ON analysis_runs(paper_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_analysis_runs_batch
            ON analysis_runs(batch_id);
        CREATE INDEX IF NOT EXISTS idx_analysis_runs_batch_created
            ON analysis_runs(batch_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_analysis_runs_status_updated
            ON analysis_runs(status, updated_at);
        CREATE INDEX IF NOT EXISTS idx_analysis_jobs_recovery
            ON analysis_jobs(status, cancel_requested, lease_until, created_at);
        CREATE INDEX IF NOT EXISTS idx_qa_messages_run_created
            ON qa_messages(run_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_citations_run_index
            ON citations(run_id, citation_index);
        CREATE INDEX IF NOT EXISTS idx_citations_paper_title
            ON citations(paper_id, title);
        CREATE INDEX IF NOT EXISTS idx_llm_usage_run_created
            ON llm_usage_events(run_id, created_at);
        """
    )
