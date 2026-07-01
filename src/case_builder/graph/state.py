"""Typed graph state shared by LangGraph and the sequential runner."""

from __future__ import annotations

from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    case_dir: str
    title: str | None
    subject: str | None
    run_id: str | None
    lanes: list[str]
    planned_commands: list[list[str]]
    tool_results: list[dict[str, Any]]
    review_required: bool
    status: str
    errors: list[str]
    runner: str
