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


def _wait_for_terminal(client, run_id, timeout=30.0):
    """Analysis runs on a background thread pool; poll until it settles."""
    deadline = time.monotonic() + timeout
    response = client.get(f"/api/runs/{run_id}")
    while time.monotonic() < deadline:
        if response.status_code == 200 and response.json()["status"] in {"completed", "failed"}:
            return response
        time.sleep(0.05)
        response = client.get(f"/api/runs/{run_id}")
    return response


pytestmark = pytest.mark.skipif(
    not SAMPLE_PDF.exists(),
    reason="sample.pdf fixture not found",
)


class TestFullPipeline:
    def test_upload_and_run_produces_report(self, isolated_settings, monkeypatch):
        from app.agents.graph import run_analysis as real_run_analysis
        from app.api import routes_papers

        def sync_run_analysis(**kwargs):
            return real_run_analysis(**kwargs)

        monkeypatch.setattr(routes_papers, "run_analysis", sync_run_analysis)

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

            detail_resp = _wait_for_terminal(client, run_id)
            assert detail_resp.status_code == 200
            assert detail_resp.json()["status"] == "completed"

            report_resp = client.get(f"/api/runs/{run_id}/report")
            assert report_resp.status_code == 200
            assert len(report_resp.json()["content"]) > 0
