#!/usr/bin/env python3
"""Run a command with the repository virtualenv Python."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def venv_python() -> Path:
    if sys.platform == "win32":
        return ROOT / ".venv" / "Scripts" / "python.exe"
    return ROOT / ".venv" / "bin" / "python"


def main(argv: list[str]) -> int:
    if not argv:
        raise SystemExit("Usage: venv_exec.py <python-args...>")

    python = venv_python()
    if not python.exists():
        raise SystemExit("Virtualenv not found. Run `moon run crk:install-dev` first.")

    return subprocess.run([str(python), *argv], cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
