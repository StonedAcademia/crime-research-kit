#!/usr/bin/env python3
"""Compatibility wrapper for running Python commands through uv."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def main(argv: list[str]) -> int:
    if not argv:
        raise SystemExit("Usage: venv_exec.py <python-args...>")

    command = [
        "uv",
        "run",
        "--cache-dir",
        ".uv-cache",
        "--no-project",
        "--with-editable",
        ".[dev]",
        "--",
        "python",
        *argv,
    ]
    return subprocess.run(command, cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
