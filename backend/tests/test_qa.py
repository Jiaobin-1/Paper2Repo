from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.database import (
    create_paper,
    create_run,
    get_qa_history,
    init_db,
    save_qa_message,
    save_report,
    update_run_status,
)
from app.main import create_app


def _client():
    return TestClient(create_app())


def _seed_completed_run(isolated_settings):
    init_db()
    pdf_path = isolated_settings / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    paper = create_paper("paper.pdf", str(pdf_path), pdf_path.stat().st_size)
    run = create_run(paper["id"])
    update_run_status(run["id"], "completed", completed=True, current_step="completed", progress_percent=100)
    report_dir = isolated_settings / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{run['id']}.md"
    report_content = "# Test Report\n\nThis paper proposes a transformer model."
    report_path.write_text(report_content, encoding="utf-8")
    save_report(run["id"], paper["id"], "Test Report", report_content, str(report_path))
    return paper, run


# ---------------------------------------------------------------------------
# Database CRUD
# ---------------------------------------------------------------------------


class TestQaDatabase:
    def test_save_and_get_qa_history(self, isolated_settings):
        paper, run = _seed_completed_run(isolated_settings)
        msg1 = save_qa_message(run["id"], paper["id"], "user", "What is the main contribution?")
        msg2 = save_qa_message(run["id"], paper["id"], "assistant", "The main contribution is...")
        assert msg1["role"] == "user"
        assert msg2["role"] == "assistant"

        history = get_qa_history(run["id"])
        assert len(history) == 2
        assert history[0]["content"] == "What is the main contribution?"
        assert history[1]["content"] == "The main contribution is..."

    def test_qa_history_ordered_by_created_at(self, isolated_settings):
        paper, run = _seed_completed_run(isolated_settings)
        save_qa_message(run["id"], paper["id"], "user", "First question")
        save_qa_message(run["id"], paper["id"], "assistant", "First answer")
        save_qa_message(run["id"], paper["id"], "user", "Second question")

        history = get_qa_history(run["id"])
        assert len(history) == 3
        assert history[0]["content"] == "First question"
        assert history[2]["content"] == "Second question"

    def test_qa_history_empty_for_new_run(self, isolated_settings):
        paper, run = _seed_completed_run(isolated_settings)
        history = get_qa_history(run["id"])
        assert history == []

    def test_delete_run_cascades_qa(self, isolated_settings):
        from app.core.database import delete_run

        paper, run = _seed_completed_run(isolated_settings)
        save_qa_message(run["id"], paper["id"], "user", "Question?")
        save_qa_message(run["id"], paper["id"], "assistant", "Answer.")

        assert len(get_qa_history(run["id"])) == 2
        delete_run(run["id"])
        assert len(get_qa_history(run["id"])) == 0


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


class TestQaApi:
    def test_get_qa_history_empty(self, isolated_settings):
        paper, run = _seed_completed_run(isolated_settings)
        with _client() as client:
            resp = client.get(f"/api/runs/{run['id']}/qa")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_qa_history_with_messages(self, isolated_settings):
        paper, run = _seed_completed_run(isolated_settings)
        save_qa_message(run["id"], paper["id"], "user", "What is this about?")
        save_qa_message(run["id"], paper["id"], "assistant", "This paper is about transformers.")

        with _client() as client:
            resp = client.get(f"/api/runs/{run['id']}/qa")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["role"] == "user"
        assert data[1]["role"] == "assistant"

    def test_get_qa_404_for_missing_run(self, isolated_settings):
        init_db()
        with _client() as client:
            resp = client.get("/api/runs/nonexistent/qa")
        assert resp.status_code == 404

    def test_post_qa_404_for_missing_run(self, isolated_settings):
        init_db()
        with _client() as client:
            resp = client.post("/api/runs/nonexistent/qa", json={"question": "Hello?"})
        assert resp.status_code == 404

    def test_post_qa_400_for_incomplete_run(self, isolated_settings):
        init_db()
        pdf_path = isolated_settings / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
        paper = create_paper("paper.pdf", str(pdf_path), pdf_path.stat().st_size)
        run = create_run(paper["id"])

        with _client() as client:
            resp = client.post(f"/api/runs/{run['id']}/qa", json={"question": "Hello?"})
        assert resp.status_code == 400

    def test_post_qa_422_for_empty_question(self, isolated_settings):
        paper, run = _seed_completed_run(isolated_settings)
        with _client() as client:
            resp = client.post(f"/api/runs/{run['id']}/qa", json={"question": ""})
        assert resp.status_code == 422

    def test_post_qa_returns_user_and_assistant(self, isolated_settings):
        paper, run = _seed_completed_run(isolated_settings)
        with _client() as client:
            resp = client.post(f"/api/runs/{run['id']}/qa", json={"question": "What is the main method?"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["role"] == "user"
        assert data[0]["content"] == "What is the main method?"
        assert data[1]["role"] == "assistant"
        assert len(data[1]["content"]) > 0

    def test_post_qa_saves_to_database(self, isolated_settings):
        paper, run = _seed_completed_run(isolated_settings)
        with _client() as client:
            client.post(f"/api/runs/{run['id']}/qa", json={"question": "Test question?"})

        history = get_qa_history(run["id"])
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_post_qa_multiple_rounds(self, isolated_settings):
        paper, run = _seed_completed_run(isolated_settings)
        with _client() as client:
            client.post(f"/api/runs/{run['id']}/qa", json={"question": "First question?"})
            client.post(f"/api/runs/{run['id']}/qa", json={"question": "Follow-up?"})

        history = get_qa_history(run["id"])
        assert len(history) == 4
