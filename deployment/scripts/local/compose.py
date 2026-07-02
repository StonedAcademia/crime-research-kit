#!/usr/bin/env python3
"""Run repository Docker Compose operations with consistent paths."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = ROOT / "deployment" / "docker-compose.yml"
ENV_FILE = ROOT / "deployment" / ".env"


COMMANDS: dict[str, list[str]] = {
    "config": ["config"],
    "build": ["build", "trcr"],
    "up": ["up", "-d"],
    "down": ["down"],
    "logs": ["logs", "-f"],
    "shell": ["exec", "trcr", "/bin/bash"],
    "pull-model": ["exec", "trcr", "deployment/scripts/local/bootstrap-ollama.sh"],
    "smoke": ["exec", "trcr", "deployment/scripts/checks/smoke/smoke-test.sh"],
}


def compose_prefix() -> list[str]:
    command = ["docker", "compose"]
    if ENV_FILE.exists():
        command.extend(["--env-file", str(ENV_FILE)])
    command.extend(["-f", str(COMPOSE_FILE)])
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=sorted(COMMANDS))
    args = parser.parse_args()

    env = os.environ.copy()
    env.setdefault("TRCR_REPO_ROOT", str(ROOT))
    command = [*compose_prefix(), *COMMANDS[args.operation]]
    print("+", " ".join(command))
    return subprocess.run(command, cwd=ROOT, env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())
