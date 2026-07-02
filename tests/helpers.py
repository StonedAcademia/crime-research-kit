"""Shared test paths that stay stable when tests move between categories."""

from __future__ import annotations

from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    search_from = current if current.is_dir() else current.parent
    for path in (search_from, *search_from.parents):
        if (path / "pyproject.toml").exists() and (path / "src" / "case_builder").exists():
            return path
    raise RuntimeError(f"Could not find tc-c-kit repo root from {current}")


KIT_ROOT = find_repo_root()
TCR_PATH = KIT_ROOT / ".agents" / "skills" / "truecrime-cult-research" / "scripts" / "tcr.py"
