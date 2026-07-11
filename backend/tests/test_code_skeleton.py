from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.database import create_paper, create_run, init_db, save_analysis_result, update_run_status
from app.main import create_app


@pytest.fixture()
def client(isolated_settings):
    with TestClient(create_app()) as test_client:
        yield test_client


def _setup_completed_run(
    tmp_path: Path,
    *,
    code_structure: list[dict] | None = None,
) -> tuple[str, str]:
    init_db()
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    paper = create_paper("test.pdf", pdf, 100)
    run = create_run(paper["id"])
    update_run_status(run["id"], "completed", completed=True)

    reproduction = {
        "minimum_reproduction_goal": "Reproduce Table 1 results",
        "reproduction_scope": ["ImageNet classification"],
        "code_structure": code_structure if code_structure is not None else [
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


def test_skeleton_download(tmp_path: Path, client: TestClient) -> None:
    run_id, _ = _setup_completed_run(tmp_path)
    response = client.get(f"/api/runs/{run_id}/skeleton")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_skeleton_zip_contents(tmp_path: Path, client: TestClient) -> None:
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


def test_skeleton_readme_content(tmp_path: Path, client: TestClient) -> None:
    run_id, _ = _setup_completed_run(tmp_path)
    response = client.get(f"/api/runs/{run_id}/skeleton")

    import io
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    readme = zf.read("README.md").decode()

    assert "Reproduce Table 1 results" in readme
    assert "ImageNet classification" in readme
    assert "Setup data" in readme


def test_skeleton_plan_content(tmp_path: Path, client: TestClient) -> None:
    run_id, _ = _setup_completed_run(tmp_path)
    response = client.get(f"/api/runs/{run_id}/skeleton")

    import io
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    plan = zf.read("PLAN.md").decode()

    assert "Implementation Plan" in plan
    assert "Setup data" in plan
    assert "Run baseline" in plan


def test_skeleton_python_stubs(tmp_path: Path, client: TestClient) -> None:
    run_id, _ = _setup_completed_run(tmp_path)
    response = client.get(f"/api/runs/{run_id}/skeleton")

    import io
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    data_py = zf.read("src/data.py").decode()

    assert "class" in data_py
    assert "TODO" in data_py or "def" in data_py


def test_skeleton_not_completed(tmp_path: Path, client: TestClient) -> None:
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    paper = create_paper("test.pdf", pdf, 100)
    run = create_run(paper["id"])
    response = client.get(f"/api/runs/{run['id']}/skeleton")
    assert response.status_code == 400


def test_skeleton_nonexistent_run(client: TestClient) -> None:
    response = client.get("/api/runs/nonexistent/skeleton")
    assert response.status_code == 404


def test_skeleton_rejects_unsafe_and_conflicting_archive_paths(tmp_path: Path, client: TestClient) -> None:
    run_id, _ = _setup_completed_run(
        tmp_path,
        code_structure=[
            {"path": "../../escape.py", "type": "file", "purpose": "unsafe"},
            {"path": "/absolute.py", "type": "file", "purpose": "unsafe"},
            {"path": r"C:\escape.py", "type": "file", "purpose": "unsafe"},
            {"path": "safe/../escape.py", "type": "file", "purpose": "unsafe"},
            {"path": "README.md", "type": "file", "purpose": "must not replace generated README"},
            {"path": "requirements.txt", "type": "file", "purpose": "must not replace generated requirements"},
            {"path": "src/module.py", "type": "file", "purpose": "safe"},
            {"path": r"src\windows.py", "type": "file", "purpose": "safe and normalized"},
            {"path": "SRC/MODULE.py", "type": "file", "purpose": "case-insensitive collision"},
        ],
    )

    response = client.get(f"/api/runs/{run_id}/skeleton")
    assert response.status_code == 200

    import io

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        names = zf.namelist()

    assert names.count("README.md") == 1
    assert names.count("requirements.txt") == 1
    assert "src/module.py" in names
    assert "src/windows.py" in names
    assert len(names) == len({name.casefold() for name in names})
    assert all(not name.startswith("/") for name in names)
    assert all(".." not in Path(name).parts for name in names)
    assert all(not name.casefold().startswith("c:") for name in names)


def test_skeleton_generated_source_escapes_untrusted_text(tmp_path: Path, client: TestClient) -> None:
    run_id, _ = _setup_completed_run(
        tmp_path,
        code_structure=[
            {
                "path": "src/9-bad-name.py",
                "type": "file",
                "purpose": 'quote """\nraise RuntimeError("injected")',
                "todo": 'finish """\nraise RuntimeError("injected")',
            },
            {
                "path": "configs/unsafe.json",
                "type": "file",
                "purpose": 'quoted "value"\nwith newline',
            },
            {
                "path": "scripts/run-$(touch-pwned).sh",
                "type": "file",
                "purpose": "comment\nprintf pwned",
            },
        ],
    )

    response = client.get(f"/api/runs/{run_id}/skeleton")
    assert response.status_code == 200

    import io

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        python_source = zf.read("src/9-bad-name.py").decode()
        json_source = zf.read("configs/unsafe.json").decode()
        shell_source = zf.read("scripts/run-$(touch-pwned).sh").decode()

    compile(python_source, "9-bad-name.py", "exec")
    assert json.loads(json_source)["_comment"] == 'quoted "value"\nwith newline'
    assert "\nprintf pwned\n" not in shell_source
    assert "echo 'Running run-$(touch-pwned)...'" in shell_source
