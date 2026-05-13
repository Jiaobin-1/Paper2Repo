from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _client():
    return TestClient(create_app())


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

        detail_response = client.get(f"/api/runs/{created_run['id']}")

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

        delete_response = client.delete(f"/api/runs/{run_id}")
        detail_response = client.get(f"/api/runs/{run_id}")

    assert delete_response.status_code == 200
    assert delete_response.json()["id"] == run_id
    assert detail_response.status_code == 404
