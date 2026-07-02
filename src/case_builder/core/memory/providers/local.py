"""Case-local JSONL workflow memory provider."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from case_builder.core.casefile import append_jsonl, case_path
from case_builder.core.memory.base import MemoryEntry


class LocalMemoryProvider:
    """Append-only local memory for tests and fully offline workflows."""

    def __init__(self, case_dir: str | Path, path: str | None = None) -> None:
        self.case_dir = case_path(case_dir)
        self.path = Path(path) if path else self.case_dir / "staging" / "memory" / "workflow_memory.jsonl"

    def add(self, entry: MemoryEntry) -> dict[str, Any]:
        row = {
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "text": entry.text,
            "metadata": entry.metadata,
            "evidence": False,
            "notes": "Workflow memory only; not a source-backed evidence record.",
        }
        append_jsonl(self.path, row)
        return {"provider": "local", "path": str(self.path), "text": entry.text}
