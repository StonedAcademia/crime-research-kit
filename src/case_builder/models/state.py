"""Serializable app models shared by CLI, graph, and tests."""

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any


def new_run_id(case_dir: str, subject: str | None = None) -> str:
    """Create a stable-enough run id without persisting global counters."""
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    digest = hashlib.sha1(f"{case_dir}|{subject or ''}|{now}".encode("utf-8")).hexdigest()[:12]
    return f"casebuild_{digest}"


@dataclass
class CaseBuilderState:
    """Serializable state passed between case-builder workflow steps."""

    case_dir: str
    title: str | None = None
    subject: str | None = None
    run_id: str | None = None
    thread_id: str | None = None
    lanes: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    packets: list[str] = field(default_factory=list)
    approved_packets: list[str] = field(default_factory=list)
    rejected_packets: list[dict[str, Any]] = field(default_factory=list)
    export_approved: bool = False
    index_enabled: bool = False
    llm_enabled: bool = False
    lane_suggestions: list[dict[str, Any]] = field(default_factory=list)
    planned_commands: list[list[str]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    review_required: bool = True
    status: str = "initialized"
    errors: list[str] = field(default_factory=list)
    runner: str = "sequential"

    def normalized(self) -> "CaseBuilderState":
        if not self.run_id:
            self.run_id = new_run_id(self.case_dir, self.subject)
        if not self.thread_id:
            self.thread_id = self.run_id
        self.lanes = dedupe(self.lanes)
        return self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.normalized())

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CaseBuilderState":
        known = set(cls.__dataclass_fields__)
        data = {key: value[key] for key in value.keys() & known}
        return cls(**data).normalized()


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out
