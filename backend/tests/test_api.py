from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.core.database import create_paper, create_run, init_db, save_report, update_run_status
from app.main import create_app


def _client():
    return TestClient(create_app())


def _wait_for_terminal(client, run_id, timeout=5.0):
    """Analysis now runs on a background thread pool; poll until it settles."""
    deadline = time.monotonic() + timeout
    response = client.get(f"/api/runs/{run_id}")
    while time.monotonic() < deadline:
        if response.status_code == 200 and response.json()["status"] in {"completed", "failed"}:
            return response
        time.sleep(0.02)
        response = client.get(f"/api/runs/{run_id}")
    return response


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
    from app.api import routes_papers

    def fake_run_analysis(**kwargs):
        kwargs["progress_callback"]("parse_pdf_node", 35)

    monkeypatch.setattr(routes_papers, "run_analysis", fake_run_analysis)

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

        detail_response = _wait_for_terminal(client, created_run["id"])

    run = detail_response.json()
    assert detail_response.status_code == 200
    assert run["status"] == "completed"
    assert run["current_step"] == "completed"
    assert run["progress_percent"] == 100
    assert run["updated_at"]


def test_delete_completed_run_removes_it_from_api(isolated_settings, monkeypatch):
    from app.api import routes_papers

    def fake_run_analysis(**kwargs):
        kwargs["progress_callback"]("persist_result_node", 100)

    monkeypatch.setattr(routes_papers, "run_analysis", fake_run_analysis)

    with _client() as client:
        upload_response = client.post(
            "/api/papers/upload",
            files={"file": ("paper.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
        )
        paper = upload_response.json()
        run_response = client.post(f"/api/papers/{paper['id']}/runs")
        run_id = run_response.json()["id"]
        _wait_for_terminal(client, run_id)

        delete_response = client.delete(f"/api/runs/{run_id}")
        detail_response = client.get(f"/api/runs/{run_id}")

    assert delete_response.status_code == 200
    assert delete_response.json()["id"] == run_id
    assert detail_response.status_code == 404


def test_delete_completed_paper_removes_records_and_files(isolated_settings):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    report_path = isolated_settings / "reports" / "run.md"
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
    pdf_path = isolated_settings / "paper.pdf"
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
