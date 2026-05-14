from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.database import (
    STALE_RUN_ERROR_MESSAGE,
    claim_analysis_job,
    create_analysis_job,
    create_paper,
    create_run,
    delete_run,
    fail_analysis_job,
    get_analysis_job,
    get_connection,
    get_run,
    init_db,
    list_recoverable_analysis_jobs,
    recover_stale_runs,
    request_analysis_cancel,
    update_run_status,
)


def test_init_db_creates_updated_at_and_run_updates(isolated_settings):
    init_db()
    with get_connection() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(analysis_runs)").fetchall()}
    assert "updated_at" in columns

    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])

    assert run["updated_at"]
    update_run_status(run["id"], "running", current_step="parse_pdf_node", progress_percent=42)
    updated_run = get_run(run["id"])

    assert updated_run["status"] == "running"
    assert updated_run["current_step"] == "parse_pdf_node"
    assert updated_run["progress_percent"] == 42
    assert updated_run["updated_at"]


def test_init_db_migrates_existing_analysis_runs_without_updated_at(isolated_settings):
    settings = get_settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat()
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute(
            """
            CREATE TABLE analysis_runs (
                id TEXT PRIMARY KEY,
                paper_id TEXT NOT NULL,
                status TEXT NOT NULL,
                model_name TEXT,
                current_step TEXT,
                progress_percent INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                started_at TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, paper_id, status, model_name, current_step, progress_percent,
                error_message, started_at, completed_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("legacy-run", "paper-1", "running", "test-model", "queued", 0, None, now, None, now),
        )

    init_db()

    with get_connection() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(analysis_runs)").fetchall()}
        row = conn.execute("SELECT updated_at, status FROM analysis_runs WHERE id = ?", ("legacy-run",)).fetchone()

    assert "updated_at" in columns
    assert row["updated_at"] == now
    assert row["status"] == "running"


def test_init_db_repairs_completed_run_progress(isolated_settings):
    settings = get_settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat()
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute(
            """
            CREATE TABLE analysis_runs (
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
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, paper_id, status, model_name, current_step, progress_percent,
                error_message, started_at, completed_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("legacy-completed", "paper-1", "completed", "test-model", "queued", 0, None, now, None, now, now),
        )

    init_db()

    repaired = get_run("legacy-completed")

    assert repaired["status"] == "completed"
    assert repaired["current_step"] == "completed"
    assert repaired["progress_percent"] == 100
    assert repaired["completed_at"]


def test_recover_stale_runs_marks_only_pending_and_running(isolated_settings):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    old = (datetime.now(UTC) - timedelta(minutes=90)).isoformat()
    now = datetime.now(UTC).isoformat()

    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO analysis_runs (
                id, paper_id, status, model_name, current_step, progress_percent,
                error_message, started_at, completed_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("run-pending", paper["id"], "pending", "test-model", "queued", 0, None, old, None, old, old),
                ("run-running", paper["id"], "running", "test-model", "persist_result_node", 99, None, old, None, old, old),
                ("run-completed", paper["id"], "completed", "test-model", "completed", 100, None, old, old, old, old),
                ("run-fresh", paper["id"], "running", "test-model", "parse_pdf_node", 10, None, now, None, now, now),
            ],
        )

    assert recover_stale_runs() == 2

    assert get_run("run-pending")["status"] == "failed"
    assert get_run("run-pending")["error_message"] == STALE_RUN_ERROR_MESSAGE
    assert get_run("run-running")["status"] == "failed"
    assert get_run("run-running")["progress_percent"] == 99
    assert get_run("run-completed")["status"] == "completed"
    assert get_run("run-fresh")["status"] == "running"


def test_delete_run_removes_run_result_and_report_rows(isolated_settings):
    from app.core.database import get_report, save_analysis_result, save_report

    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    report_path = isolated_settings / "reports" / "run.md"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("report", encoding="utf-8")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])
    update_run_status(run["id"], "completed", completed=True, current_step="completed", progress_percent=100)
    save_analysis_result(run["id"], paper["id"], {})
    save_report(run["id"], paper["id"], "Report", "content", report_path)

    deleted = delete_run(run["id"])

    assert deleted["id"] == run["id"]
    assert get_run(run["id"]) is None
    assert get_report(run["id"]) is None


def test_analysis_job_lifecycle_and_recovery(isolated_settings):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])

    job = create_analysis_job(run["id"], paper["id"], max_attempts=2)

    assert job["status"] == "pending"
    assert claim_analysis_job(run["id"]) == "claimed"
    assert get_analysis_job(run["id"])["attempts"] == 1
    assert fail_analysis_job(run["id"], "temporary") == "pending"
    assert list_recoverable_analysis_jobs()[0]["run_id"] == run["id"]
    assert claim_analysis_job(run["id"]) == "claimed"
    assert fail_analysis_job(run["id"], "final") == "failed"


def test_analysis_job_cancel_request(isolated_settings):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])
    create_analysis_job(run["id"], paper["id"])

    assert request_analysis_cancel(run["id"]) is True
    assert claim_analysis_job(run["id"]) == "canceled"
    assert get_analysis_job(run["id"])["status"] == "canceled"
    assert fail_analysis_job(run["id"], "canceled") == "canceled"
