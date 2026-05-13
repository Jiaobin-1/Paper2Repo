from __future__ import annotations

from app.api import routes_papers
from app.core.database import create_paper, create_run, get_run, init_db


def test_run_analysis_background_marks_completed(isolated_settings, monkeypatch):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])

    def fake_run_analysis(**kwargs):
        kwargs["progress_callback"]("persist_result_node", 100)

    monkeypatch.setattr(routes_papers, "run_analysis", fake_run_analysis)

    routes_papers.run_analysis_background(paper["id"], run["id"], str(pdf_path), "test-model")
    updated_run = get_run(run["id"])

    assert updated_run["status"] == "completed"
    assert updated_run["current_step"] == "completed"
    assert updated_run["progress_percent"] == 100
    assert updated_run["completed_at"]


def test_run_analysis_background_marks_failed(isolated_settings, monkeypatch):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", pdf_path, pdf_path.stat().st_size)
    run = create_run(paper["id"])

    def fake_run_analysis(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(routes_papers, "run_analysis", fake_run_analysis)

    routes_papers.run_analysis_background(paper["id"], run["id"], str(pdf_path), "test-model")
    updated_run = get_run(run["id"])

    assert updated_run["status"] == "failed"
    assert updated_run["current_step"] == "failed"
    assert updated_run["error_message"] == "boom"
    assert updated_run["completed_at"]
