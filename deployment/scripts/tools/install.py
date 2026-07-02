#!/usr/bin/env python3
"""Compatibility wrapper for warming CRK command environments with uv."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def normalize_extras(values: list[str]) -> list[str]:
    extras: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part and part not in extras:
                extras.append(part)
    return extras


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv", default=".venv", help="Legacy option; only .venv is supported.")
    parser.add_argument("--extras", action="append", default=[], help="Optional dependency extra, or comma-separated extras.")
    parser.add_argument("--dev", action="store_true", help="Sync the dev extra.")
    parser.add_argument("--recreate", action="store_true", help="Delete the local project environment before syncing.")
    parser.add_argument("--skip-pip-upgrade", action="store_true", help="Legacy no-op retained for compatibility.")
    args = parser.parse_args()

    if args.venv != ".venv":
        raise SystemExit("Custom --venv paths are not supported; use uv project environments.")

    if args.recreate:
        shutil.rmtree(ROOT / ".venv", ignore_errors=True)

    extras = normalize_extras(args.extras)
    if args.dev and "dev" not in extras:
        extras.insert(0, "dev")

    requirement = f".[{','.join(extras)}]" if extras else "."
    command = [
        "uv",
        "run",
        "--cache-dir",
        ".uv-cache",
        "--no-project",
        "--with-editable",
        requirement,
        "--",
        "python",
        "-c",
        "print('CRK environment ready')",
    ]

    print("+", " ".join(command))
    return subprocess.run(command, cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
