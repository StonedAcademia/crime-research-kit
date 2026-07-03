"""Subprocess executor for the packaged CRK ledger CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence

from .result import OpResult


LEDGER_CLI_MODULE = "crime_research_kit._runtime.adapters.interfaces.cli"


class CrkRunner:
    """Low-level executor that turns ledger CLI invocations into OpResults."""

    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        dry_run: bool = True,
        python_executable: str | None = None,
    ) -> None:
        self.repo_root = repo_root or default_repo_root()
        self.dry_run = dry_run
        self.python_executable = python_executable or sys.executable
        self.cli_module = LEDGER_CLI_MODULE

    def command(self, args: Sequence[str]) -> list[str]:
        return [self.python_executable, "-m", self.cli_module, *args]

    def case_path(self, case_dir: str) -> Path:
        path = Path(case_dir)
        return path if path.is_absolute() else self.repo_root / path

    def run(self, name: str, args: Sequence[str]) -> OpResult:
        command = self.command(args)
        if self.dry_run:
            return OpResult(name=name, command=command, dry_run=True)
        completed = subprocess.run(
            command,
            cwd=self.repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        ok = completed.returncode == 0
        stderr = completed.stderr.strip()
        return OpResult(
            name=name,
            ok=ok,
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout.strip(),
            stderr=stderr,
            errors=[] if ok else [stderr or f"{name} failed with code {completed.returncode}"],
        )


def default_repo_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "case.json").exists() or (cwd / "pyproject.toml").exists() or (cwd / "tc-c-kit").exists():
        return cwd
    return cwd
