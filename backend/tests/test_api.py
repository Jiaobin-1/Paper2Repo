from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.core.database import (
    create_paper,
    create_run,
    init_db,
    save_analysis_result,
    save_report,
    update_run_status,
)
from app.main import create_app


def _client():
    return TestClient(create_app())


def _wait_for_terminal_run(client: TestClient, run_id: str, timeout: float = 2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/runs/{run_id}")
        if response.json()["status"] in {"completed", "failed"}:
            return response
        time.sleep(0.01)
    raise AssertionError(f"Run {run_id} did not reach a terminal state.")


def test_upload_rejects_non_pdf_extension(isolated_settings):
    with _client() as client:
        response = client.post(
            "/api/papers/upload",
            files={"file": ("paper.txt", b"%PDF-1.4\n%%EOF", "application/pdf")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are supported."


def test_upload_rejects_invalid_pdf_signature(isolated_settings):
    with _client() as client:
        response = client.post(
            "/api/papers/upload",
            files={"file": ("paper.pdf", b"not a pdf", "application/pdf")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is not a valid PDF."
    assert list((isolated_settings / "uploads").glob("*")) == []


def test_upload_rejects_too_large_pdf_and_removes_partial_file(isolated_settings):
    oversized = b"%PDF-" + (b"x" * (1024 * 1024 + 1))
    with _client() as client:
        response = client.post(
            "/api/papers/upload",
            files={"file": ("large.pdf", oversized, "application/pdf")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "PDF file is too large. Maximum size is 1 MB."
    assert list((isolated_settings / "uploads").glob("*")) == []


def test_upload_accepts_valid_pdf_and_start_run_success(isolated_settings, monkeypatch):
    from app.services import analysis_runner

    def fake_run_analysis(**kwargs):
        kwargs["progress_callback"]("parse_pdf_node", 35)
        report_path = isolated_settings / f"{kwargs['run_id']}.md"
        report_path.write_text("# Test report\n", encoding="utf-8")
        save_analysis_result(kwargs["run_id"], kwargs["paper_id"], {})
        save_report(kwargs["run_id"], kwargs["paper_id"], "Test report", "# Test report\n", report_path)
        return {
            "persist_result": {
                "paper_id": kwargs["paper_id"],
                "run_id": kwargs["run_id"],
                "status": "completed",
                "report_path": str(report_path),
            }
        }

    monkeypatch.setattr(analysis_runner, "run_analysis", fake_run_analysis)

    with _client() as client:
        upload_response = client.post(
            "/api/papers/upload",
            files={"file": ("paper.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
        )
        assert upload_response.status_code == 200
        paper = upload_response.json()
        assert paper["file_size"] == len(b"%PDF-1.4\n%%EOF")

        run_response = client.post(f"/api/papers/{paper['id']}/runs")
        assert run_response.status_code == 200
        created_run = run_response.json()
        assert created_run["updated_at"]

        detail_response = _wait_for_terminal_run(client, created_run["id"])

    run = detail_response.json()
    assert detail_response.status_code == 200
    assert run["status"] == "completed"
    assert run["current_step"] == "completed"
    assert run["progress_percent"] == 100
    assert run["updated_at"]


def test_start_run_returns_503_and_rolls_back_when_analysis_queue_is_full(isolated_settings, monkeypatch):
    from app.services import analysis_runner

    def reject_submission(*_args, **_kwargs):
        raise analysis_runner.AnalysisQueueFullError("Analysis queue is full. Please retry later.")

    monkeypatch.setattr(analysis_runner, "submit_analysis", reject_submission)

    with _client() as client:
        upload_response = client.post(
            "/api/papers/upload",
            files={"file": ("paper.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
        )
        paper_id = upload_response.json()["id"]
        response = client.post(f"/api/papers/{paper_id}/runs")
        runs_response = client.get(f"/api/papers/{paper_id}/runs")

    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert runs_response.json() == []


def test_queue_status_endpoint_returns_capacity(isolated_settings):
    with _client() as client:
        response = client.get("/api/runs/queue")

    assert response.status_code == 200
    payload = response.json()
    assert payload["capacity"] == payload["max_workers"] + payload["max_queued_jobs"]
    assert payload["available_slots"] <= payload["capacity"]
    assert payload["retry_after_seconds"] == 5


def test_storage_summary_and_cleanup_remove_orphan_files(isolated_settings, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("STORAGE_CLEANUP_MIN_AGE_HOURS", "0")
    get_settings.cache_clear()

    uploads = isolated_settings / "uploads"
    reports = isolated_settings / "reports"
    uploads.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    orphan_upload = uploads / "orphan.pdf"
    orphan_report = reports / "orphan.md"
    orphan_upload.write_bytes(b"%PDF-1.4\n%%EOF")
    orphan_report.write_text("orphan", encoding="utf-8")

    with _client() as client:
        summary_response = client.get("/api/storage/summary")
        cleanup_response = client.post("/api/storage/cleanup?dry_run=false")
        after_response = client.get("/api/storage/summary")

    assert summary_response.status_code == 200
    assert summary_response.json()["orphan_file_count"] == 2
    assert cleanup_response.status_code == 200
    assert cleanup_response.json()["deleted_file_count"] == 2
    assert not orphan_upload.exists()
    assert not orphan_report.exists()
    assert after_response.json()["orphan_file_count"] == 0


def test_delete_completed_run_removes_it_from_api(isolated_settings, monkeypatch):
    from app.services import analysis_runner

    def fake_run_analysis(**kwargs):
        kwargs["progress_callback"]("persist_result_node", 100)

    monkeypatch.setattr(analysis_runner, "run_analysis", fake_run_analysis)

    with _client() as client:
        upload_response = client.post(
            "/api/papers/upload",
            files={"file": ("paper.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
        )
        paper = upload_response.json()
        run_response = client.post(f"/api/papers/{paper['id']}/runs")
        run_id = run_response.json()["id"]
        _wait_for_terminal_run(client, run_id)
        delete_response = client.delete(f"/api/runs/{run_id}")
        detail_response = client.get(f"/api/runs/{run_id}")

    assert delete_response.status_code == 200
    assert delete_response.json()["id"] == run_id
    assert detail_response.status_code == 404


def test_batch_upload_rejects_invalid_pdf_without_partial_files_or_papers(isolated_settings):
    with _client() as client:
        response = client.post(
            "/api/papers/upload-batch",
            files=[
                ("files", ("valid.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")),
                ("files", ("invalid.pdf", b"not a pdf", "application/pdf")),
            ],
        )
        papers_response = client.get("/api/papers")

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is not a valid PDF."
    assert papers_response.json() == []
    assert list((isolated_settings / "uploads").glob("*")) == []


def test_batch_upload_rejects_non_pdf_without_partial_files_or_papers(isolated_settings):
    with _client() as client:
        response = client.post(
            "/api/papers/upload-batch",
            files=[
                ("files", ("valid.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")),
                ("files", ("notes.txt", b"%PDF-1.4\n%%EOF", "application/pdf")),
            ],
        )
        papers_response = client.get("/api/papers")

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are supported. Rejected: notes.txt"
    assert papers_response.json() == []
    assert list((isolated_settings / "uploads").glob("*")) == []


def test_batch_upload_rejects_total_size_without_partial_files_or_papers(isolated_settings, monkeypatch):
    from app.api import routes_papers

    monkeypatch.setattr(routes_papers, "MAX_BATCH_TOTAL_SIZE", 1024 * 1024)
    pdf_bytes = b"%PDF-" + (b"x" * (600 * 1024))

    with _client() as client:
        response = client.post(
            "/api/papers/upload-batch",
            files=[
                ("files", ("one.pdf", pdf_bytes, "application/pdf")),
                ("files", ("two.pdf", pdf_bytes, "application/pdf")),
            ],
        )
        papers_response = client.get("/api/papers")

    assert response.status_code == 400
    assert response.json()["detail"] == "Total batch size exceeds 1 MB limit."
    assert papers_response.json() == []
    assert list((isolated_settings / "uploads").glob("*")) == []


def test_delete_completed_paper_removes_records_and_files(isolated_settings):
    init_db()
    pdf_path = isolated_settings / "uploads" / "paper.pdf"
    report_path = isolated_settings / "reports" / "run.md"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("# Report", encoding="utf-8")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])
    update_run_status(run["id"], "completed", completed=True, current_step="completed", progress_percent=100)
    save_report(run["id"], paper["id"], "Report", "# Report", report_path)

    with _client() as client:
        delete_response = client.delete(f"/api/papers/{paper['id']}")
        paper_response = client.get(f"/api/papers/{paper['id']}")
        run_response = client.get(f"/api/runs/{run['id']}")

    assert delete_response.status_code == 200
    assert delete_response.json()["id"] == paper["id"]
    assert paper_response.status_code == 404
    assert run_response.status_code == 404
    assert not pdf_path.exists()
    assert not report_path.exists()


def test_delete_paper_rejects_active_runs(isolated_settings):
    init_db()
    pdf_path = isolated_settings / "uploads" / "paper.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    create_run(paper["id"])

    with _client() as client:
        delete_response = client.delete(f"/api/papers/{paper['id']}")
        paper_response = client.get(f"/api/papers/{paper['id']}")

    assert delete_response.status_code == 409
    assert delete_response.json()["detail"] == "Paper has pending or running analyses."
    assert paper_response.status_code == 200
    assert pdf_path.exists()
