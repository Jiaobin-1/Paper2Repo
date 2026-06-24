from __future__ import annotations

from app.core.database import (
    create_analysis_job,
    create_paper,
    create_run,
    get_analysis_job,
    get_run,
    init_db,
    request_analysis_cancel,
)
from app.services import analysis_runner


def test_run_analysis_background_marks_completed(isolated_settings, monkeypatch):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])
    create_analysis_job(run["id"], paper["id"])

    def fake_run_analysis(**kwargs):
        kwargs["progress_callback"]("persist_result_node", 100)

    monkeypatch.setattr(analysis_runner, "run_analysis", fake_run_analysis)

    analysis_runner.run_analysis_background(paper["id"], run["id"], str(pdf_path), "test-model")
    updated_run = get_run(run["id"])

    assert updated_run["status"] == "completed"
    assert updated_run["current_step"] == "completed"
    assert updated_run["progress_percent"] == 100
    assert updated_run["completed_at"]
    assert get_analysis_job(run["id"])["status"] == "completed"


def test_run_analysis_background_retries_transient_failure(isolated_settings, monkeypatch):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])
    create_analysis_job(run["id"], paper["id"], max_attempts=2)
    calls = 0

    def fake_run_analysis(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary")
        kwargs["progress_callback"]("persist_result_node", 100)

    monkeypatch.setattr(analysis_runner, "run_analysis", fake_run_analysis)

    analysis_runner.run_analysis_background(paper["id"], run["id"], str(pdf_path), "test-model")
    updated_run = get_run(run["id"])
    job = get_analysis_job(run["id"])

    assert calls == 2
    assert updated_run["status"] == "completed"
    assert updated_run["current_step"] == "completed"
    assert updated_run["progress_percent"] == 100
    assert job["status"] == "completed"
    assert job["attempts"] == 2


def test_run_analysis_background_marks_failed_after_attempts(isolated_settings, monkeypatch):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])
    create_analysis_job(run["id"], paper["id"], max_attempts=2)
    calls = 0

    def fake_run_analysis(**kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError("boom")

    monkeypatch.setattr(analysis_runner, "run_analysis", fake_run_analysis)

    analysis_runner.run_analysis_background(paper["id"], run["id"], str(pdf_path), "test-model")
    updated_run = get_run(run["id"])
    job = get_analysis_job(run["id"])

    assert calls == 2
    assert updated_run["status"] == "failed"
    assert updated_run["current_step"] == "failed"
    assert updated_run["error_message"] == "boom"
    assert updated_run["completed_at"]
    assert job["status"] == "failed"
    assert job["attempts"] == 2


def test_run_analysis_background_marks_missing_job_failed(isolated_settings, monkeypatch):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])
    calls = 0

    def fake_run_analysis(**kwargs):
        nonlocal calls
        calls += 1

    monkeypatch.setattr(analysis_runner, "run_analysis", fake_run_analysis)

    analysis_runner.run_analysis_background(paper["id"], run["id"], str(pdf_path), "test-model")
    updated_run = get_run(run["id"])

    assert calls == 0
    assert updated_run["status"] == "failed"
    assert updated_run["current_step"] == "failed"
    assert updated_run["error_message"] == analysis_runner.MISSING_JOB_ERROR_MESSAGE
    assert updated_run["completed_at"]


def test_run_analysis_background_does_not_retry_canceled_job(isolated_settings, monkeypatch):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])
    create_analysis_job(run["id"], paper["id"], max_attempts=2)
    request_analysis_cancel(run["id"])
    calls = 0

    def fake_run_analysis(**kwargs):
        nonlocal calls
        calls += 1

    monkeypatch.setattr(analysis_runner, "run_analysis", fake_run_analysis)

    analysis_runner.run_analysis_background(paper["id"], run["id"], str(pdf_path), "test-model")
    updated_run = get_run(run["id"])
    job = get_analysis_job(run["id"])

    assert calls == 0
    assert updated_run["status"] == "failed"
    assert updated_run["current_step"] == "failed"
    assert updated_run["error_message"] == "Analysis canceled."
    assert job["status"] == "canceled"
