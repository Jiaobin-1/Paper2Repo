from __future__ import annotations

import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.database import create_paper, create_run, init_db, save_analysis_result, update_run_status
from app.main import app

client = TestClient(app)


def _setup_completed_run(tmp_path: Path) -> tuple[str, str]:
    init_db()
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    paper = create_paper("test.pdf", pdf, 100)
    run = create_run(paper["id"])
    update_run_status(run["id"], "completed", completed=True)

    reproduction = {
        "minimum_reproduction_goal": "Reproduce Table 1 results",
        "reproduction_scope": ["ImageNet classification"],
        "code_structure": [
            {"path": "src/data.py", "type": "file", "purpose": "Data loading", "todo": "Implement dataset"},
            {"path": "src/model.py", "type": "file", "purpose": "Model definition", "todo": "Implement model"},
            {"path": "configs", "type": "directory", "purpose": "Configuration files", "todo": ""},
            {"path": "configs/default.yaml", "type": "file", "purpose": "Default config", "todo": ""},
        ],
        "required_modules": [
            {
                "name": "data",
                "purpose": "Data pipeline",
                "inputs": ["images"],
                "outputs": ["tensors"],
                "todos": ["Load dataset", "Apply transforms"],
            },
            {
                "name": "model",
                "purpose": "Model architecture",
                "inputs": ["tensors"],
                "outputs": ["logits"],
                "todos": ["Build model"],
            },
        ],
        "implementation_steps": [
            {"step": 1, "title": "Setup data", "description": "Load and preprocess data", "expected_output": "DataLoader"},
            {"step": 2, "title": "Build model", "description": "Implement model architecture", "expected_output": "Model class"},
        ],
        "experiment_checklist": [
            {"item": "Run baseline", "done": False},
            {"item": "Run ablation", "done": False},
        ],
    }
    save_analysis_result(run["id"], paper["id"], {"reproduction_plan": reproduction})
    return run["id"], paper["id"]


def test_skeleton_download(tmp_path: Path) -> None:
    run_id, _ = _setup_completed_run(tmp_path)
    response = client.get(f"/api/runs/{run_id}/skeleton")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_skeleton_zip_contents(tmp_path: Path) -> None:
    run_id, _ = _setup_completed_run(tmp_path)
    response = client.get(f"/api/runs/{run_id}/skeleton")

    import io
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    names = zf.namelist()

    assert ".gitignore" in names
    assert "README.md" in names
    assert "PLAN.md" in names
    assert "src/data.py" in names
    assert "src/model.py" in names
    assert "configs/.gitkeep" in names
    assert "configs/default.yaml" in names
    assert "requirements.txt" in names


def test_skeleton_readme_content(tmp_path: Path) -> None:
    run_id, _ = _setup_completed_run(tmp_path)
    response = client.get(f"/api/runs/{run_id}/skeleton")

    import io
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    readme = zf.read("README.md").decode()

    assert "Reproduce Table 1 results" in readme
    assert "ImageNet classification" in readme
    assert "Setup data" in readme


def test_skeleton_plan_content(tmp_path: Path) -> None:
    run_id, _ = _setup_completed_run(tmp_path)
    response = client.get(f"/api/runs/{run_id}/skeleton")

    import io
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    plan = zf.read("PLAN.md").decode()

    assert "Implementation Plan" in plan
    assert "Setup data" in plan
    assert "Run baseline" in plan


def test_skeleton_python_stubs(tmp_path: Path) -> None:
    run_id, _ = _setup_completed_run(tmp_path)
    response = client.get(f"/api/runs/{run_id}/skeleton")

    import io
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    data_py = zf.read("src/data.py").decode()

    assert "class" in data_py
    assert "TODO" in data_py or "def" in data_py


def test_skeleton_not_completed(tmp_path: Path) -> None:
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    paper = create_paper("test.pdf", pdf, 100)
    run = create_run(paper["id"])
    response = client.get(f"/api/runs/{run['id']}/skeleton")
    assert response.status_code == 400


def test_skeleton_nonexistent_run() -> None:
    response = client.get("/api/runs/nonexistent/skeleton")
    assert response.status_code == 404
