#!/usr/bin/env python3
"""Run the lightweight repository checks used by local development."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run([sys.executable, "-m", "compileall", "src", ".agents/skills/truecrime-cult-research/scripts"])
    run([sys.executable, ".agents/skills/truecrime-cult-research/scripts/tcr.py", "validate", "data/examples/synthetic_case"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
