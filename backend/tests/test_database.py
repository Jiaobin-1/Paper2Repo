from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import get_settings
from app.core.database import (
    STALE_RUN_ERROR_MESSAGE,
    claim_analysis_job,
    create_analysis_job,
    create_citations,
    create_paper,
    create_run,
    delete_paper,
    delete_run,
    fail_analysis_job,
    get_all_embeddings,
    get_analysis_job,
    get_analysis_result,
    get_citations_for_run,
    get_connection,
    get_llm_usage_summary,
    get_paper,
    get_paper_chunks,
    get_paper_storage_paths,
    get_qa_history,
    get_report,
    get_run,
    init_db,
    list_recoverable_analysis_jobs,
    paper_has_active_runs,
    recover_stale_runs,
    replace_chunks,
    request_analysis_cancel,
    save_analysis_result,
    save_embeddings,
    save_llm_usage_events,
    save_qa_message,
    save_report,
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


def test_init_db_enables_foreign_keys_and_query_indexes(isolated_settings):
    init_db()
    with get_connection() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        index_names = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
        }

    assert {
        "idx_papers_created_at",
        "idx_paper_chunks_paper_chunk",
        "idx_analysis_runs_paper_created",
        "idx_analysis_runs_status_updated",
        "idx_analysis_runs_batch_created",
        "idx_analysis_jobs_recovery",
        "idx_qa_messages_run_created",
        "idx_paper_embeddings_paper_chunk",
        "idx_citations_run_index",
        "idx_citations_paper_title",
    } <= index_names


def test_foreign_keys_reject_orphan_run(isolated_settings):
    init_db()
    now = datetime.now(UTC).isoformat()
    with pytest.raises(sqlite3.IntegrityError), get_connection() as conn:
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, paper_id, status, current_step, progress_percent,
                started_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("orphan", "missing-paper", "pending", "queued", 0, now, now, now),
        )


def test_llm_usage_summary_aggregates_tokens_cost_and_latency(isolated_settings):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])
    save_llm_usage_events(
        run["id"],
        [
            {
                "model": "test-model",
                "mode": "responses_structured",
                "operation": "PaperMetadata",
                "input_tokens": 100,
                "output_tokens": 25,
                "total_tokens": 125,
                "estimated_cost_usd": 0.0002,
                "latency_ms": 50,
                "attempts": 1,
            },
            {
                "model": "test-model",
                "mode": "chat",
                "operation": "chat",
                "input_tokens": 20,
                "output_tokens": 10,
                "total_tokens": 30,
                "estimated_cost_usd": 0.0001,
                "latency_ms": 25,
                "attempts": 1,
            },
        ],
    )

    summary = get_llm_usage_summary(run["id"])

    assert summary["call_count"] == 2
    assert summary["input_tokens"] == 120
    assert summary["output_tokens"] == 35
    assert summary["total_tokens"] == 155
    assert summary["estimated_cost_usd"] == 0.0003
    assert summary["latency_ms"] == 75


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
    create_citations(
        run["id"],
        paper["id"],
        [{"index": 1, "authors": "A", "title": "Cited Paper", "raw_text": "A. Cited Paper."}],
    )

    deleted = delete_run(run["id"])

    assert deleted["id"] == run["id"]
    assert get_run(run["id"]) is None
    assert get_report(run["id"]) is None
    assert get_citations_for_run(run["id"]) == []


def test_delete_paper_removes_all_dependent_rows(isolated_settings):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    report_path = isolated_settings / "reports" / "run.md"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("report", encoding="utf-8")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])
    update_run_status(run["id"], "completed", completed=True, current_step="completed", progress_percent=100)
    create_analysis_job(run["id"], paper["id"])
    replace_chunks(
        paper["id"],
        [
            {
                "content": "chunk content",
                "metadata": {"chunk_index": 0, "page_start": 1, "page_end": 1, "section_title": "Intro"},
            }
        ],
    )
    save_embeddings(paper["id"], [(0, b"embedding")])
    save_analysis_result(run["id"], paper["id"], {"metadata": {"title": "Paper"}})
    save_report(run["id"], paper["id"], "Report", "content", report_path)
    save_qa_message(run["id"], paper["id"], "user", "Question?")
    save_llm_usage_events(
        run["id"],
        [
            {
                "model": "test-model",
                "mode": "chat",
                "operation": "chat",
                "input_tokens": 2,
                "output_tokens": 3,
                "total_tokens": 5,
                "estimated_cost_usd": 0.0001,
                "latency_ms": 10,
                "attempts": 1,
            }
        ],
    )
    create_citations(
        run["id"],
        paper["id"],
        [{"index": 1, "authors": "A", "title": "Cited Paper", "raw_text": "A. Cited Paper."}],
    )

    assert paper_has_active_runs(paper["id"]) is False
    assert set(get_paper_storage_paths(paper["id"])) == {str(pdf_path), str(report_path)}
    assert get_llm_usage_summary(run["id"])["call_count"] == 1

    deletion = delete_paper(paper["id"])

    assert deletion.status == "deleted"
    assert deletion.paper is not None
    assert deletion.paper["id"] == paper["id"]
    assert set(deletion.storage_paths) == {str(pdf_path), str(report_path)}
    assert get_paper(paper["id"]) is None
    assert get_run(run["id"]) is None
    assert get_analysis_job(run["id"]) is None
    assert get_analysis_result(run["id"]) is None
    assert get_report(run["id"]) is None
    assert get_qa_history(run["id"]) == []
    assert get_citations_for_run(run["id"]) == []
    assert get_paper_chunks(paper["id"]) == []
    assert get_all_embeddings() == []
    assert get_llm_usage_summary(run["id"])["call_count"] == 0


def test_paper_has_active_runs_detects_pending_and_running(isolated_settings):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])

    assert paper_has_active_runs(paper["id"]) is True
    deletion = delete_paper(paper["id"])
    assert deletion.status == "active_runs"
    assert get_paper(paper["id"]) is not None

    update_run_status(run["id"], "failed", completed=True, current_step="failed")
    assert paper_has_active_runs(paper["id"]) is False


def test_delete_paper_reports_not_found(isolated_settings):
    init_db()

    deletion = delete_paper("missing-paper")

    assert deletion.status == "not_found"
    assert deletion.paper is None


def test_analysis_job_lifecycle_and_recovery(isolated_settings):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])

    job = create_analysis_job(run["id"], paper["id"], max_attempts=2)

    assert job["status"] == "pending"
    assert claim_analysis_job(run["id"]) == "claimed"
    assert claim_analysis_job(run["id"]) == "busy"
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
