from __future__ import annotations

import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from app.core.database import get_analysis_result, get_paper, get_run

logger = logging.getLogger(__name__)

_GITIGNORE = """\
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg
.venv/
venv/
env/
.env
*.so
.DS_Store
*.log
wandb/
outputs/
checkpoints/
*.pt
*.pth
*.ckpt
"""


def generate_skeleton_zip(run_id: str) -> Path:
    run = get_run(run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found.")
    if run["status"] != "completed":
        raise ValueError(f"Run {run_id} is not completed.")

    analysis = get_analysis_result(run_id)
    if not analysis:
        raise ValueError(f"Analysis result not found for run {run_id}.")

    reproduction = analysis.get("reproduction_json") or {}
    paper = get_paper(run["paper_id"])

    paper_title = (paper or {}).get("title") or "Untitled Paper"
    code_structure = reproduction.get("code_structure", [])
    modules = reproduction.get("required_modules", [])
    steps = reproduction.get("implementation_steps", [])
    checklist = reproduction.get("experiment_checklist", [])
    goal = reproduction.get("minimum_reproduction_goal", "")
    scope = reproduction.get("reproduction_scope", [])

    tmp = tempfile.mkdtemp()
    zip_path = Path(tmp) / f"skeleton_{run_id[:8]}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        _add_gitignore(zf)
        _add_readme(zf, paper_title, goal, scope, steps, modules)
        _add_plan(zf, steps, checklist, modules)
        _add_structure(zf, code_structure, modules, paper_title)
        if not any(item.get("path") == "requirements.txt" for item in code_structure):
            _add_requirements(zf, modules)

    return zip_path


def _add_gitignore(zf: zipfile.ZipFile) -> None:
    zf.writestr(".gitignore", _GITIGNORE)


def _add_readme(
    zf: zipfile.ZipFile,
    title: str,
    goal: str,
    scope: list[str],
    steps: list[dict[str, Any]],
    modules: list[dict[str, Any]],
) -> None:
    lines = [
        f"# {title} — Reproduction",
        "",
        "## Goal",
        goal or "Reproduce the paper's main results.",
        "",
        "## Scope",
    ]
    for s in scope:
        lines.append(f"- {s}")
    if not scope:
        lines.append("- Full reproduction of the paper's main contributions")

    lines.extend(["", "## Quick Start", "", "```bash", "pip install -r requirements.txt", "```", ""])

    if steps:
        lines.append("## Implementation Steps")
        lines.append("")
        for step in steps:
            lines.append(f"{step.get('step', '?')}. **{step.get('title', '')}** — {step.get('description', '')}")
        lines.append("")

    if modules:
        lines.append("## Modules")
        lines.append("")
        for mod in modules:
            lines.append(f"- **{mod.get('name', '')}**: {mod.get('purpose', '')}")
        lines.append("")

    zf.writestr("README.md", "\n".join(lines))


def _add_plan(
    zf: zipfile.ZipFile,
    steps: list[dict[str, Any]],
    checklist: list[dict[str, Any]],
    modules: list[dict[str, Any]],
) -> None:
    lines = ["# Implementation Plan", ""]

    if steps:
        lines.append("## Steps")
        lines.append("")
        for step in steps:
            lines.append(f"### Step {step.get('step', '?')}: {step.get('title', '')}")
            lines.append("")
            lines.append(step.get("description", ""))
            if step.get("expected_output"):
                lines.append(f"\n**Expected output:** {step['expected_output']}")
            lines.append("")

    if modules:
        lines.append("## Modules")
        lines.append("")
        for mod in modules:
            lines.append(f"### {mod.get('name', '')}")
            lines.append(f"\n{mod.get('purpose', '')}")
            if mod.get("inputs"):
                lines.append(f"\n**Inputs:** {', '.join(mod['inputs'])}")
            if mod.get("outputs"):
                lines.append(f"\n**Outputs:** {', '.join(mod['outputs'])}")
            if mod.get("todos"):
                lines.append("\n**TODOs:**")
                for todo in mod["todos"]:
                    lines.append(f"- [ ] {todo}")
            lines.append("")

    if checklist:
        lines.append("## Checklist")
        lines.append("")
        for item in checklist:
            mark = "x" if item.get("done") else " "
            lines.append(f"- [{mark}] {item.get('item', '')}")
        lines.append("")

    zf.writestr("PLAN.md", "\n".join(lines))


def _add_structure(
    zf: zipfile.ZipFile,
    code_structure: list[dict[str, Any]],
    modules: list[dict[str, Any]],
    paper_title: str,
) -> None:
    module_map = {m.get("name", ""): m for m in modules}

    for item in code_structure:
        path = item.get("path", "")
        item_type = item.get("type", "file")
        purpose = item.get("purpose", "")
        todo = item.get("todo", "")

        if item_type == "directory":
            zf.writestr(f"{path}/.gitkeep", "")
            continue

        if not path:
            continue

        ext = Path(path).suffix.lower()
        content = _generate_file_content(path, ext, purpose, todo, module_map, paper_title)
        zf.writestr(path, content)


def _generate_file_content(
    path: str,
    ext: str,
    purpose: str,
    todo: str,
    module_map: dict[str, dict[str, Any]],
    paper_title: str,
) -> str:
    basename = Path(path).stem

    if ext == ".py":
        return _py_stub(basename, purpose, todo, module_map)
    if ext in (".yaml", ".yml"):
        return _yaml_stub(basename, purpose)
    if ext == ".json":
        return _json_stub(basename, purpose)
    if ext == ".sh":
        return _sh_stub(basename, purpose)
    if basename.lower() == "readme":
        return f"# {paper_title}\n\n{purpose}\n"
    return f"# {purpose}\n# TODO: {todo}\n"


def _py_stub(
    name: str,
    purpose: str,
    todo: str,
    module_map: dict[str, dict[str, Any]],
) -> str:
    lines = [
        '"""',
        f"{purpose}",
        '"""',
        "",
    ]

    related = module_map.get(name)
    if related:
        if related.get("inputs"):
            lines.append(f"# Expected inputs: {', '.join(related['inputs'])}")
        if related.get("outputs"):
            lines.append(f"# Expected outputs: {', '.join(related['outputs'])}")
        lines.append("")

    if name == "data" or "data" in name.lower():
        lines.extend([
            "import torch",
            "from torch.utils.data import Dataset, DataLoader",
            "",
            "",
            f"class {name.title().replace('_', '')}Dataset(Dataset):",
            f'    """{purpose}"""',
            "",
            "    def __init__(self, data_path: str):",
            "        # TODO: Load and preprocess data",
            "        pass",
            "",
            "    def __len__(self) -> int:",
            "        raise NotImplementedError",
            "",
            "    def __getitem__(self, idx: int):",
            "        raise NotImplementedError",
            "",
            "",
            "def get_dataloader(data_path: str, batch_size: int = 32, shuffle: bool = True) -> DataLoader:",
            f'    """Create a DataLoader for {name}."""',
            f"    dataset = {name.title().replace('_', '')}Dataset(data_path)",
            "    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)",
            "",
        ])
    elif name == "train" or "train" in name.lower():
        lines.extend([
            "import argparse",
            "",
            "",
            "def train(config_path: str):",
            f'    """{purpose}"""',
            "    # TODO: Implement training loop",
            "    raise NotImplementedError",
            "",
            "",
            'if __name__ == "__main__":',
            "    parser = argparse.ArgumentParser()",
            '    parser.add_argument("--config", type=str, default="configs/default.yaml")',
            "    args = parser.parse_args()",
            "    train(args.config)",
            "",
        ])
    elif name == "evaluate" or "eval" in name.lower():
        lines.extend([
            "import argparse",
            "",
            "",
            "def evaluate(model_path: str, data_path: str):",
            f'    """{purpose}"""',
            "    # TODO: Implement evaluation",
            "    raise NotImplementedError",
            "",
            "",
            'if __name__ == "__main__":',
            "    parser = argparse.ArgumentParser()",
            '    parser.add_argument("--model", type=str, required=True)',
            '    parser.add_argument("--data", type=str, required=True)',
            "    args = parser.parse_args()",
            "    evaluate(args.model, args.data)",
            "",
        ])
    else:
        class_name = "".join(w.title() for w in name.replace("-", "_").split("_"))
        lines.extend([
            "",
            "",
            f"class {class_name}:",
            f'    """{purpose}"""',
            "",
            "    def __init__(self):",
            "        # TODO: Initialize",
            "        pass",
            "",
            "    def run(self):",
            f'        """TODO: {todo}"""',
            "        raise NotImplementedError",
            "",
        ])

    if todo:
        lines.extend([f"# TODO: {todo}", ""])

    return "\n".join(lines)


def _yaml_stub(name: str, purpose: str) -> str:
    return f"""# {purpose}
# TODO: Configure parameters

model:
  name: ""
  pretrained: false

data:
  path: ""
  batch_size: 32

training:
  lr: 0.001
  epochs: 100
  seed: 42
"""


def _json_stub(name: str, purpose: str) -> str:
    return f"""{{
  "_comment": "{purpose}",
  "model": {{}},
  "data": {{}},
  "training": {{}}
}}
"""


def _sh_stub(name: str, purpose: str) -> str:
    return f"""#!/bin/bash
# {purpose}
set -euo pipefail

# TODO: Add commands
echo "Running {name}..."
"""


def _add_requirements(zf: zipfile.ZipFile, modules: list[dict[str, Any]]) -> None:
    deps = {"torch", "numpy", "tqdm", "pyyaml"}

    for mod in modules:
        name = mod.get("name", "").lower()
        purpose = mod.get("purpose", "").lower()
        if "image" in name or "vision" in purpose or "image" in purpose:
            deps.add("torchvision")
        if "nlp" in name or "text" in purpose or "language" in purpose:
            deps.add("transformers")
            deps.add("tokenizers")
        if "graph" in name or "gnn" in purpose:
            deps.add("torch-geometric")

    lines = sorted(deps)
    zf.writestr("requirements.txt", "\n".join(lines) + "\n")
