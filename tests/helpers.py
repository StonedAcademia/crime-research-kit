"""Shared test paths that stay stable when tests move between categories."""

from __future__ import annotations

import re
from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    search_from = current if current.is_dir() else current.parent
    for path in (search_from, *search_from.parents):
        if (path / "pyproject.toml").exists() and (path / "src" / "cli.py").exists():
            return path
    raise RuntimeError(f"Could not find tc-c-kit repo root from {current}")


KIT_ROOT = find_repo_root()
TCR_PATH = KIT_ROOT / ".agents" / "skills" / "truecrime-cult-research" / "scripts" / "tcr.py"


def moon_task_names() -> set[str]:
    task_files = [KIT_ROOT / "moon.yml", *sorted((KIT_ROOT / ".moon" / "tasks").glob("*.yml"))]
    names: set[str] = set()
    for path in task_files:
        in_tasks = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.match(r"^[A-Za-z0-9_-]+:", line):
                in_tasks = line.startswith("tasks:")
                continue
            if in_tasks and line and not line.startswith((" ", "\t")):
                in_tasks = False
                continue
            match = re.match(r"^  ([A-Za-z0-9_-]+):(?:\s|$)", line)
            if in_tasks and match:
                names.add(match.group(1))
    return names
