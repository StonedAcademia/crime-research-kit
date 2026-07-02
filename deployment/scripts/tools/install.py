#!/usr/bin/env python3
"""Create the local virtualenv and install TRCR in editable mode."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def ensure_pip(python: Path) -> None:
    probe = subprocess.run([str(python), "-m", "pip", "--version"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if probe.returncode != 0:
        run([str(python), "-m", "ensurepip", "--upgrade"])


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
    parser.add_argument("--venv", default=".venv", help="Virtualenv path relative to the repository root.")
    parser.add_argument("--extras", action="append", default=[], help="Optional dependency extra, or comma-separated extras.")
    parser.add_argument("--dev", action="store_true", help="Install the dev extra.")
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate the virtualenv first.")
    parser.add_argument("--skip-pip-upgrade", action="store_true", help="Do not upgrade pip before installing.")
    args = parser.parse_args()

    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or newer is required.")

    venv_dir = (ROOT / args.venv).resolve()
    if args.recreate and venv_dir.exists():
        shutil.rmtree(venv_dir)

    if not venv_dir.exists():
        print(f"Creating virtualenv: {venv_dir}")
        venv.EnvBuilder(with_pip=True).create(venv_dir)

    python = venv_python(venv_dir)
    if not python.exists():
        raise SystemExit(f"Virtualenv Python not found: {python}")

    ensure_pip(python)
    if not args.skip_pip_upgrade:
        run([str(python), "-m", "pip", "install", "--upgrade", "pip"])

    extras = normalize_extras(args.extras)
    if args.dev and "dev" not in extras:
        extras.insert(0, "dev")
    editable = f".[{','.join(extras)}]" if extras else "."
    run([str(python), "-m", "pip", "install", "-e", editable])

    if sys.platform == "win32":
        activate = venv_dir / "Scripts" / "Activate.ps1"
    else:
        activate = venv_dir / "bin" / "activate"
    print(f"Installed TRCR into {venv_dir}")
    print(f"Activate with: {activate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
