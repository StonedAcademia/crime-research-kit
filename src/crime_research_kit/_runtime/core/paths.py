"""Path helpers for source-checkout aware runtime code."""

from __future__ import annotations

from pathlib import Path


def source_repo_root(start: Path) -> Path | None:
    """Find the repository root from a moved runtime module path."""
    for parent in (start, *start.parents):
        if (parent / "pyproject.toml").is_file() and (parent / "docs").is_dir():
            return parent
    return None
