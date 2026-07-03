"""Shared test paths that stay stable when tests move between categories."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    search_from = current if current.is_dir() else current.parent
    for path in (search_from, *search_from.parents):
        if (path / "pyproject.toml").exists() and (path / "src" / "crime_research_kit" / "_runtime" / "cli.py").exists():
            return path
    raise RuntimeError(f"Could not find tc-c-kit repo root from {current}")


KIT_ROOT = find_repo_root()
LEDGER_CLI_MODULE = "crime_research_kit._runtime.adapters.interfaces.cli"


def load_ledger_cli() -> SimpleNamespace:
    from crime_research_kit._runtime.adapters.interfaces.cli.app import app, build_click_command
    from crime_research_kit._runtime.adapters.interfaces.cli.entry import main
    from crime_research_kit._runtime.adapters.ops.casework.records.names.parsing import parse_name_entries
    from crime_research_kit._runtime.core.casefile import (
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
        app=app,
        command_tree=build_click_command(),
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


DOCS_FIXTURE = KIT_ROOT / "tests" / "fixtures" / "docs" / "sample_report.pdf"


def requires_extra(module_name: str):
    return pytest.importorskip(module_name)


def requires_binary(name: str) -> None:
    if shutil.which(name) is None:
        pytest.skip(f"required binary not on PATH: {name}")


def live_service(url: str | None, health_path: str) -> str:
    if not url:
        pytest.skip("live service URL not configured")
    base = url.rstrip("/")
    try:
        response = httpx.get(base + health_path, timeout=2.0)
        response.raise_for_status()
    except Exception as exc:  # connection refused, timeout, non-2xx
        pytest.skip(f"live service not reachable at {base}{health_path}: {exc}")
    return base


def register_pdf_source(case_dir, source_id: str, pdf_path):
    from pathlib import Path as _Path
    import shutil as _shutil

    from crime_research_kit._runtime.core.casefile import append_jsonl, record_path

    case_dir = _Path(case_dir)
    rel = f"raw/sources/{source_id}.pdf"
    dest = case_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    _shutil.copyfile(_Path(pdf_path), dest)
    append_jsonl(
        record_path(case_dir, "sources"),
        {
            "source_id": source_id,
            "title": f"Fixture source {source_id}",
            "source_type": "document",
            "raw_path": rel,
            "public_export": True,
            "reliability_grade": "C",
            "notes": "Synthetic fixture source; not real evidence.",
        },
    )
    return rel
