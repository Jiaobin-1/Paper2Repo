from __future__ import annotations

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


def _seed_run_with_report(isolated_settings):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", str(pdf_path), pdf_path.stat().st_size)
    run = create_run(paper["id"])
    update_run_status(run["id"], "completed", completed=True, current_step="completed", progress_percent=100)
    save_analysis_result(run["id"], paper["id"], {
        "metadata": {"title": "Test Paper", "authors": ["A"], "abstract": "Abs", "keywords": ["k"]},
        "classification": {"domain": "llm", "paper_type": "experimental"},
    })
    report_dir = isolated_settings / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{run['id']}.md"
    report_content = "# Test Report\n\nContent here."
    report_path.write_text(report_content, encoding="utf-8")
    save_report(run["id"], paper["id"], "Test Report", report_content, str(report_path))
    return paper, run


class TestGetRuns:
    def test_list_runs_returns_all_runs(self, isolated_settings):
        paper, run = _seed_run_with_report(isolated_settings)
        with _client() as client:
            resp = client.get("/api/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(r["id"] == run["id"] for r in data)

    def test_list_runs_with_paper_id_filter(self, isolated_settings):
        paper, run = _seed_run_with_report(isolated_settings)
        with _client() as client:
            resp = client.get(f"/api/runs?paper_id={paper['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert all(r["paper_id"] == paper["id"] for r in data)

    def test_list_runs_respects_limit(self, isolated_settings):
        paper, _ = _seed_run_with_report(isolated_settings)
        for _ in range(4):
            r = create_run(paper["id"])
            update_run_status(r["id"], "completed", completed=True)
        with _client() as client:
            resp = client.get("/api/runs?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestGetRunAnalysis:
    def test_returns_analysis_result(self, isolated_settings):
        _, run = _seed_run_with_report(isolated_settings)
        with _client() as client:
            resp = client.get(f"/api/runs/{run['id']}/analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == run["id"]
        assert "metadata" in data

    def test_returns_404_for_missing_run(self, isolated_settings):
        with _client() as client:
            resp = client.get("/api/runs/nonexistent/analysis")
        assert resp.status_code == 404

    def test_returns_404_for_missing_analysis(self, isolated_settings):
        init_db()
        pdf_path = isolated_settings / "p.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
        paper = create_paper("p.pdf", str(pdf_path), 0)
        run = create_run(paper["id"])
        update_run_status(run["id"], "completed", completed=True)
        with _client() as client:
            resp = client.get(f"/api/runs/{run['id']}/analysis")
        assert resp.status_code == 404


class TestGetRunReport:
    def test_returns_report_metadata_and_content(self, isolated_settings):
        _, run = _seed_run_with_report(isolated_settings)
        with _client() as client:
            resp = client.get(f"/api/runs/{run['id']}/report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Report"
        assert "Content here" in data["content"]

    def test_returns_404_for_missing_report(self, isolated_settings):
        init_db()
        pdf_path = isolated_settings / "p.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
        paper = create_paper("p.pdf", str(pdf_path), 0)
        run = create_run(paper["id"])
        update_run_status(run["id"], "completed", completed=True)
        with _client() as client:
            resp = client.get(f"/api/runs/{run['id']}/report")
        assert resp.status_code == 404


class TestDownloadReportMarkdown:
    def test_downloads_md_file(self, isolated_settings):
        _, run = _seed_run_with_report(isolated_settings)
        with _client() as client:
            resp = client.get(f"/api/runs/{run['id']}/report.md")
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]
        assert "Content-Disposition" in resp.headers
        assert b"# Test Report" in resp.content


class TestDownloadReportPdf:
    def test_downloads_pdf_file(self, isolated_settings):
        _, run = _seed_run_with_report(isolated_settings)
        with _client() as client:
            resp = client.get(f"/api/runs/{run['id']}/report.pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:5] == b"%PDF-"
