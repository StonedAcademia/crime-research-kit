"""Case lifecycle operations."""

from __future__ import annotations

import json
from typing import Any

from ..casefile import RECORD_FILES, ensure_case, load_records
from .result import OpResult, local_op
from .runner import CrkRunner


def init_case(runner: CrkRunner, case_dir: str, title: str | None = None) -> OpResult:
    case_path = runner.case_path(case_dir)
    args = ["init-case", case_dir, "--title", title or case_path.name.replace("_", " ").title()]
    if (case_path / "case.json").exists():
        return OpResult(name="init_case", command=runner.command(args), dry_run=runner.dry_run, skipped=True)
    return runner.run("init_case", args)


def case_info(case_dir: str) -> OpResult:
    return local_op("case_info", _case_info_data, case_dir)


def validate(runner: CrkRunner, case_dir: str) -> OpResult:
    return runner.run("validate", ["validate", case_dir])


def report(runner: CrkRunner, case_dir: str) -> OpResult:
    return runner.run("report", ["report", case_dir])


def _case_info_data(case_dir: str) -> dict[str, Any]:
    case = ensure_case(case_dir)
    meta = json.loads((case / "case.json").read_text(encoding="utf-8"))
    counts = {name: len(load_records(case, name)) for name in RECORD_FILES}
    return {"case_id": str(meta.get("case_id") or case.name), "case_json": meta, "record_counts": counts}
