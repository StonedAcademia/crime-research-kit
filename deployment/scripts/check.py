#!/usr/bin/env python3
"""Run the lightweight repository checks used by local development."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def venv_python() -> Path:
    if sys.platform == "win32":
        return ROOT / ".venv" / "Scripts" / "python.exe"
    return ROOT / ".venv" / "bin" / "python"


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    python = venv_python()
    if not python.exists():
        raise SystemExit("Virtualenv not found. Run `moon run trcr:install-dev` first.")

    run([str(python), "-m", "compileall", "src/case_builder", ".agents/skills/truecrime-cult-research/scripts"])
    run([str(python), ".agents/skills/truecrime-cult-research/scripts/tcr.py", "validate", "data/examples/synthetic_case"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
