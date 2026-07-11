from __future__ import annotations

import json
import logging
import re
import shlex
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from app.core.database import get_analysis_result, get_paper, get_run

logger = logging.getLogger(__name__)

MAX_CODE_STRUCTURE_ITEMS = 200
MAX_ARCHIVE_PATH_LENGTH = 240
MAX_ARCHIVE_PATH_PART_LENGTH = 100
RESERVED_ARCHIVE_MEMBERS = frozenset({".gitignore", "README.md", "PLAN.md", "requirements.txt"})
_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")

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
    used_members = {name.casefold() for name in zf.namelist()}
    used_members.update(name.casefold() for name in RESERVED_ARCHIVE_MEMBERS)

    for item in code_structure[:MAX_CODE_STRUCTURE_ITEMS]:
        raw_path = str(item.get("path", ""))
        path = _safe_archive_path(raw_path)
        item_type = item.get("type", "file")
        purpose = str(item.get("purpose", ""))
        todo = str(item.get("todo", ""))

        if path is None:
            logger.warning("Skipping unsafe generated skeleton path: %r", raw_path)
            continue

        if item_type == "directory":
            member = f"{path}/.gitkeep"
            if _archive_path_conflicts(member, used_members):
                logger.warning("Skipping conflicting generated skeleton path: %r", raw_path)
                continue
            zf.writestr(member, "")
            used_members.add(member.casefold())
            continue

        if item_type != "file":
            logger.warning("Skipping generated skeleton path with unknown type %r: %r", item_type, raw_path)
            continue

        if _archive_path_conflicts(path, used_members):
            logger.warning("Skipping conflicting generated skeleton path: %r", raw_path)
            continue

        ext = Path(path).suffix.lower()
        content = _generate_file_content(path, ext, purpose, todo, module_map, paper_title)
        zf.writestr(path, content)
        used_members.add(path.casefold())


def _safe_archive_path(path_value: str) -> str | None:
    """Return a portable relative ZIP member path or reject unsafe input."""
    raw = path_value.strip().replace("\\", "/")
    if not raw or raw.startswith("/") or _WINDOWS_DRIVE_PATTERN.match(raw):
        return None
    raw = raw.rstrip("/")
    if not raw or len(raw) > MAX_ARCHIVE_PATH_LENGTH:
        return None
    if any(ord(char) < 32 for char in raw):
        return None

    parts = raw.split("/")
    if any(
        part in {"", ".", ".."}
        or len(part) > MAX_ARCHIVE_PATH_PART_LENGTH
        or part.rstrip(" .") != part
        for part in parts
    ):
        return None
    return PurePosixPath(*parts).as_posix()


def _archive_path_conflicts(member: str, used_members: set[str]) -> bool:
    key = member.casefold()
    if key in used_members:
        return True

    parents = PurePosixPath(member).parents
    if any(str(parent).casefold() in used_members for parent in parents if str(parent) != "."):
        return True

    prefix = f"{key.rstrip('/')}/"
    return any(existing.startswith(prefix) for existing in used_members)


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
    return f"# {_single_line(purpose)}\n# TODO: {_single_line(todo)}\n"


def _py_stub(
    name: str,
    purpose: str,
    todo: str,
    module_map: dict[str, dict[str, Any]],
) -> str:
    purpose_text = str(purpose)
    todo_text = str(todo)
    class_name = _python_class_name(name)
    lines = [
        json.dumps(purpose_text, ensure_ascii=False),
        "",
    ]

    related = module_map.get(name)
    if related:
        if related.get("inputs"):
            lines.append(f"# Expected inputs: {_single_line(', '.join(map(str, related['inputs'])))}")
        if related.get("outputs"):
            lines.append(f"# Expected outputs: {_single_line(', '.join(map(str, related['outputs'])))}")
        lines.append("")

    if name == "data" or "data" in name.lower():
        lines.extend([
            "import torch",
            "from torch.utils.data import Dataset, DataLoader",
            "",
            "",
            f"class {class_name}Dataset(Dataset):",
            f"    {json.dumps(purpose_text, ensure_ascii=False)}",
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
            f"    {json.dumps(f'Create a DataLoader for {name}.', ensure_ascii=False)}",
            f"    dataset = {class_name}Dataset(data_path)",
            "    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)",
            "",
        ])
    elif name == "train" or "train" in name.lower():
        lines.extend([
            "import argparse",
            "",
            "",
            "def train(config_path: str):",
            f"    {json.dumps(purpose_text, ensure_ascii=False)}",
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
            f"    {json.dumps(purpose_text, ensure_ascii=False)}",
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
        lines.extend([
            "",
            "",
            f"class {class_name}:",
            f"    {json.dumps(purpose_text, ensure_ascii=False)}",
            "",
            "    def __init__(self):",
            "        # TODO: Initialize",
            "        pass",
            "",
            "    def run(self):",
            f"        {json.dumps(f'TODO: {todo_text}', ensure_ascii=False)}",
            "        raise NotImplementedError",
            "",
        ])

    if todo_text:
        lines.extend([f"# TODO: {_single_line(todo_text)}", ""])

    return "\n".join(lines)


def _yaml_stub(name: str, purpose: str) -> str:
    return f"""# {_single_line(purpose)}
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
    return json.dumps(
        {
            "_comment": purpose,
            "model": {},
            "data": {},
            "training": {},
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def _sh_stub(name: str, purpose: str) -> str:
    message = shlex.quote(f"Running {name}...")
    return f"""#!/bin/bash
# {_single_line(purpose)}
set -euo pipefail

# TODO: Add commands
echo {message}
"""


def _single_line(value: str) -> str:
    return " ".join(str(value).splitlines()).strip()


def _python_class_name(value: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", value)
    class_name = "".join(word[:1].upper() + word[1:] for word in words) or "GeneratedModule"
    if class_name[0].isdigit():
        class_name = f"Generated{class_name}"
    return class_name


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
