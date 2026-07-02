"""Optional LLM agent nodes for the case-builder graph."""

from __future__ import annotations

from typing import Any, Callable

from ..llm.audit_brief import write_readiness_brief
from ..llm.lane_suggest import suggest_lanes
from ..llm.packet_agent import PacketAgentError, fill_packet
from ..ops import extraction as extraction_ops
from ..ops import query as query_ops
from .nodes import required_case_dir
from .state import GraphState

ModelFactory = Callable[[], Any]
AUDIT_NAMES = {
    "audit_contradictions",
    "review_narrative_readiness",
    "audit_privacy_redactions",
    "audit_source_independence",
}


def llm_active(state: GraphState, runner, model_factory: ModelFactory | None) -> bool:
    return bool(state.get("llm_enabled")) and model_factory is not None and not runner.dry_run


def suggest_lanes_node(runner, model_factory: ModelFactory | None):
    def node(state: GraphState) -> GraphState:
        if not llm_active(state, runner, model_factory):
            return {"status": "lane_suggestions_skipped"}
        suggestions = suggest_lanes(
            model_factory(),
            state.get("subject") or "",
            state.get("lanes") or [],
        )
        return {"lane_suggestions": suggestions, "status": "lanes_suggested"}

    return node


def fill_packets_node(runner, model_factory: ModelFactory | None):
    def node(state: GraphState) -> GraphState:
        if not llm_active(state, runner, model_factory):
            return {"status": "fill_skipped"}
        case_dir = required_case_dir(state)
        model = model_factory()
        errors = list(state.get("errors") or [])
        filled_count = 0
        for name in state.get("packets") or []:
            packet_result = extraction_ops.read_packet(case_dir, name)
            if not packet_result.ok:
                errors.extend(packet_result.errors)
                continue
            packet = packet_result.data["packet"]
            source_id = str(packet.get("source_id") or name.split("_extraction")[0])
            text_result = query_ops.get_source_text(case_dir, source_id, include_private=True)
            if not text_result.ok:
                errors.extend(text_result.errors)
                continue
            try:
                filled = fill_packet(model, packet, text_result.data["text"], source_id=source_id)
            except PacketAgentError as exc:
                errors.append(f"fill_packets {name}: {exc}")
                continue
            saved = extraction_ops.save_packet(case_dir, name, filled)
            if not saved.ok:
                errors.extend(saved.errors)
                continue
            filled_count += 1
        return {
            "errors": errors,
            "status": "packets_filled" if filled_count or not errors else "error",
        }

    return node


def readiness_brief_node(runner, model_factory: ModelFactory | None):
    def node(state: GraphState) -> GraphState:
        if not llm_active(state, runner, model_factory):
            return {"status": "brief_skipped"}
        case_dir = required_case_dir(state)
        audit_results = [
            item for item in (state.get("tool_results") or []) if item.get("name") in AUDIT_NAMES
        ]
        path = write_readiness_brief(model_factory(), case_dir, audit_results)
        return {
            "tool_results": [
                *(state.get("tool_results") or []),
                {"name": "readiness_brief", "ok": True, "data": {"path": path}},
            ],
            "status": "readiness_brief_written",
        }

    return node
