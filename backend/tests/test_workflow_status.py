from __future__ import annotations

import threading
import time

import pytest

from app.core.config import get_settings
from app.core.database import (
    claim_analysis_job,
    create_analysis_job,
    create_paper,
    create_run,
    get_analysis_job,
    get_connection,
    get_run,
    init_db,
    request_analysis_cancel,
    save_analysis_result,
    save_report,
)
from app.services import analysis_runner


def _persist_fake_artifacts(*, paper_id: str, run_id: str, report_dir) -> dict[str, object]:
    report_path = report_dir / f"{run_id}.md"
    report_path.write_text("# Test report\n", encoding="utf-8")
    save_analysis_result(run_id, paper_id, {})
    save_report(run_id, paper_id, "Test report", "# Test report\n", report_path)
    return {
        "persist_result": {
            "paper_id": paper_id,
            "run_id": run_id,
            "status": "completed",
            "report_path": str(report_path),
        }
    }


def test_run_analysis_background_marks_completed(isolated_settings, monkeypatch):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])
    create_analysis_job(run["id"], paper["id"])

    def fake_run_analysis(**kwargs):
        kwargs["progress_callback"]("persist_result_node", 100)
        return _persist_fake_artifacts(
            paper_id=kwargs["paper_id"], run_id=kwargs["run_id"], report_dir=isolated_settings,
        )

    monkeypatch.setattr(analysis_runner, "run_analysis", fake_run_analysis)

    analysis_runner.run_analysis_background(paper["id"], run["id"], str(pdf_path), "test-model")
    updated_run = get_run(run["id"])

    assert updated_run["status"] == "completed"
    assert updated_run["current_step"] == "completed"
    assert updated_run["progress_percent"] == 100
    assert updated_run["completed_at"]
    assert get_analysis_job(run["id"])["status"] == "completed"


def test_run_analysis_background_rejects_missing_persisted_artifacts(isolated_settings, monkeypatch):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])
    create_analysis_job(run["id"], paper["id"], max_attempts=1)
    monkeypatch.setattr(analysis_runner, "run_analysis", lambda **_kwargs: {})

    analysis_runner.run_analysis_background(paper["id"], run["id"], str(pdf_path), "test-model")

    updated_run = get_run(run["id"])
    assert updated_run["status"] == "failed"
    assert "PersistResult" in updated_run["error_message"]


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
        return _persist_fake_artifacts(
            paper_id=kwargs["paper_id"], run_id=kwargs["run_id"], report_dir=isolated_settings,
        )

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


def test_cancel_requested_during_final_node_cannot_be_overwritten_as_completed(isolated_settings, monkeypatch):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])
    create_analysis_job(run["id"], paper["id"])

    def fake_run_analysis(**_kwargs):
        request_analysis_cancel(run["id"])

    monkeypatch.setattr(analysis_runner, "run_analysis", fake_run_analysis)

    analysis_runner.run_analysis_background(paper["id"], run["id"], str(pdf_path), "test-model")

    assert get_run(run["id"])["status"] == "failed"
    assert get_run(run["id"])["error_message"] == "Analysis canceled."
    assert get_analysis_job(run["id"])["status"] == "canceled"


def test_shared_dispatcher_limits_concurrent_analysis(isolated_settings, monkeypatch):
    monkeypatch.setenv("ANALYSIS_MAX_WORKERS", "2")
    get_settings.cache_clear()
    analysis_runner.stop_analysis_dispatcher()
    init_db()
    active = 0
    maximum_active = 0
    lock = threading.Lock()

    def fake_run_analysis(**kwargs):
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        try:
            time.sleep(0.03)
            kwargs["progress_callback"]("persist_result_node", 99)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(analysis_runner, "run_analysis", fake_run_analysis)
    futures = []
    for index in range(5):
        pdf_path = isolated_settings / f"paper-{index}.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
        paper = create_paper(pdf_path.name, pdf_path, pdf_path.stat().st_size)
        run = create_run(paper["id"])
        create_analysis_job(run["id"], paper["id"])
        futures.append(analysis_runner.submit_analysis(paper["id"], run["id"], str(pdf_path), "test-model"))

    try:
        for future in futures:
            future.result(timeout=2)
    finally:
        analysis_runner.stop_analysis_dispatcher()

    assert maximum_active == 2


def test_dispatcher_rejects_work_when_running_and_queue_slots_are_full(isolated_settings, monkeypatch):
    monkeypatch.setenv("ANALYSIS_MAX_WORKERS", "1")
    monkeypatch.setenv("ANALYSIS_MAX_QUEUED_JOBS", "1")
    get_settings.cache_clear()
    analysis_runner.stop_analysis_dispatcher()
    init_db()
    started = threading.Event()
    release = threading.Event()

    def fake_run_analysis(**kwargs):
        started.set()
        release.wait(timeout=2)
        kwargs["progress_callback"]("persist_result_node", 99)

    monkeypatch.setattr(analysis_runner, "run_analysis", fake_run_analysis)
    submissions = []
    runs = []
    for index in range(3):
        pdf_path = isolated_settings / f"queued-{index}.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
        paper = create_paper(pdf_path.name, pdf_path, pdf_path.stat().st_size)
        run = create_run(paper["id"])
        create_analysis_job(run["id"], paper["id"])
        runs.append((paper, run, pdf_path))

    try:
        paper, run, pdf_path = runs[0]
        submissions.append(analysis_runner.submit_analysis(paper["id"], run["id"], str(pdf_path), "test-model"))
        assert started.wait(timeout=1)
        paper, run, pdf_path = runs[1]
        submissions.append(analysis_runner.submit_analysis(paper["id"], run["id"], str(pdf_path), "test-model"))
        paper, run, pdf_path = runs[2]
        with pytest.raises(analysis_runner.AnalysisQueueFullError):
            analysis_runner.submit_analysis(paper["id"], run["id"], str(pdf_path), "test-model")
    finally:
        release.set()
        for future in submissions:
            future.result(timeout=2)
        analysis_runner.stop_analysis_dispatcher()


def test_expired_job_is_recovered_after_interrupted_worker(isolated_settings, monkeypatch):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])
    create_analysis_job(run["id"], paper["id"])
    assert claim_analysis_job(run["id"]) == "claimed"
    with get_connection() as conn:
        conn.execute(
            "UPDATE analysis_jobs SET lease_until = ? WHERE run_id = ?",
            ("2000-01-01T00:00:00+00:00", run["id"]),
        )

    def fake_run_analysis(**kwargs):
        kwargs["progress_callback"]("persist_result_node", 99)
        return _persist_fake_artifacts(
            paper_id=kwargs["paper_id"], run_id=kwargs["run_id"], report_dir=isolated_settings,
        )

    monkeypatch.setattr(analysis_runner, "run_analysis", fake_run_analysis)

    try:
        assert analysis_runner.start_recoverable_analysis_jobs() == 1
    finally:
        analysis_runner.stop_analysis_dispatcher()

    assert get_run(run["id"])["status"] == "completed"
    assert get_analysis_job(run["id"])["status"] == "completed"
