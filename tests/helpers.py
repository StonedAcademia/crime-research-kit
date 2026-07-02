"""Shared test paths that stay stable when tests move between categories."""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    search_from = current if current.is_dir() else current.parent
    for path in (search_from, *search_from.parents):
        if (path / "pyproject.toml").exists() and (path / "src" / "cli.py").exists():
            return path
    raise RuntimeError(f"Could not find tc-c-kit repo root from {current}")


KIT_ROOT = find_repo_root()
LEDGER_CLI_MODULE = "adapters.interfaces.cli"


def load_ledger_cli() -> SimpleNamespace:
    from adapters.interfaces.cli.entry import main
    from adapters.interfaces.cli.parser import build_parser
    from adapters.ops.casework.records.names.parsing import parse_name_entries
    from core.casefile import (
        append_jsonl,
        case_path,
        read_jsonl,
        record_path,
        records_dir,
        slugify,
        stable_id,
        today,
        write_json,
        write_jsonl,
    )

    return SimpleNamespace(
        append_jsonl=append_jsonl,
        build_parser=build_parser,
        case_path=case_path,
        main=main,
        parse_name_entries=parse_name_entries,
        read_jsonl=read_jsonl,
        record_path=record_path,
        records_dir=records_dir,
        slugify=slugify,
        stable_id=stable_id,
        today=today,
        write_json=write_json,
        write_jsonl=write_jsonl,
    )


def ledger_command_args(command: list[str]) -> list[str]:
    if command[1:3] == ["-m", LEDGER_CLI_MODULE]:
        return command[3:]
    return command


def ledger_subcommand(command: list[str]) -> str:
    return ledger_command_args(command)[0]


def moon_task_names() -> set[str]:
    task_files = [KIT_ROOT / "moon.yml", *sorted((KIT_ROOT / ".moon" / "tasks").glob("*.yml"))]
    names: set[str] = set()
    for path in task_files:
        in_tasks = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.match(r"^[A-Za-z0-9_-]+:", line):
                in_tasks = line.startswith("tasks:")
                continue
            if in_tasks and line and not line.startswith((" ", "\t")):
                in_tasks = False
                continue
            match = re.match(r"^  ([A-Za-z0-9_-]+):(?:\s|$)", line)
            if in_tasks and match:
                names.add(match.group(1))
    return names
