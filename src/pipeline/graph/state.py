"""Typed graph state shared by LangGraph and the sequential runner."""

from __future__ import annotations

from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    case_dir: str
    title: str | None
    subject: str | None
    run_id: str | None
    thread_id: str | None
    lanes: list[str]
    source_urls: list[str]
    source_ids: list[str]
    packets: list[str]
    approved_packets: list[str]
    rejected_packets: list[dict[str, Any]]
    export_approved: bool
    index_enabled: bool
    llm_enabled: bool
    qdrant_url: str | None
    embed_model: str | None
    lane_suggestions: list[dict[str, Any]]
    planned_commands: list[list[str]]
    tool_results: list[dict[str, Any]]
    review_required: bool
    status: str
    errors: list[str]
    runner: str
