from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_PDF = FIXTURES / "sample.pdf"


def _client():
    return TestClient(create_app())


def _wait_for_terminal_run(client: TestClient, run_id: str, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/runs/{run_id}")
        if response.json()["status"] in {"completed", "failed"}:
            return response
        time.sleep(0.01)
    raise AssertionError(f"Run {run_id} did not reach a terminal state.")


pytestmark = pytest.mark.skipif(
    not SAMPLE_PDF.exists(),
    reason="sample.pdf fixture not found",
)


class TestFullPipeline:
    def test_upload_and_run_produces_report(self, isolated_settings, monkeypatch):
        from app.agents.graph import run_analysis as real_run_analysis
        from app.services import analysis_runner

        def sync_run_analysis(**kwargs):
            return real_run_analysis(**kwargs)

        monkeypatch.setattr(analysis_runner, "run_analysis", sync_run_analysis)

        pdf_bytes = SAMPLE_PDF.read_bytes()

        with _client() as client:
            upload_resp = client.post(
                "/api/papers/upload",
                files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
            )
            assert upload_resp.status_code == 200
            paper_id = upload_resp.json()["id"]

            run_resp = client.post(f"/api/papers/{paper_id}/runs")
            assert run_resp.status_code == 200
            run_id = run_resp.json()["id"]

            detail_resp = _wait_for_terminal_run(client, run_id)
            assert detail_resp.status_code == 200
            assert detail_resp.json()["status"] == "completed"

            report_resp = client.get(f"/api/runs/{run_id}/report")
            assert report_resp.status_code == 200
            assert len(report_resp.json()["content"]) > 0

            markdown_resp = client.get(f"/api/runs/{run_id}/report.md")
            assert markdown_resp.status_code == 200
            assert "text/markdown" in markdown_resp.headers["content-type"]
            assert len(markdown_resp.content) > 0

            pdf_resp = client.get(f"/api/runs/{run_id}/report.pdf")
            assert pdf_resp.status_code == 200
            assert pdf_resp.headers["content-type"] == "application/pdf"
            assert pdf_resp.content[:5] == b"%PDF-"

            html_resp = client.get(f"/api/runs/{run_id}/report.html")
            assert html_resp.status_code == 200
            assert "text/html" in html_resp.headers["content-type"]
            assert b"<html" in html_resp.content.lower()

            latex_resp = client.get(f"/api/runs/{run_id}/report.tex")
            assert latex_resp.status_code == 200
            assert "application/x-latex" in latex_resp.headers["content-type"]
            assert b"\\documentclass" in latex_resp.content

            markdown_resp = client.get(f"/api/runs/{run_id}/report.md")
            assert markdown_resp.status_code == 200
            assert "text/markdown" in markdown_resp.headers["content-type"]
            assert len(markdown_resp.content) > 0

            pdf_resp = client.get(f"/api/runs/{run_id}/report.pdf")
            assert pdf_resp.status_code == 200
            assert pdf_resp.headers["content-type"] == "application/pdf"
            assert pdf_resp.content[:5] == b"%PDF-"

            html_resp = client.get(f"/api/runs/{run_id}/report.html")
            assert html_resp.status_code == 200
            assert "text/html" in html_resp.headers["content-type"]
            assert b"<html" in html_resp.content.lower()

            latex_resp = client.get(f"/api/runs/{run_id}/report.tex")
            assert latex_resp.status_code == 200
            assert "application/x-latex" in latex_resp.headers["content-type"]
            assert b"\\documentclass" in latex_resp.content
