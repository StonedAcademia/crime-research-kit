"""Small graph nodes that adapt agent policy to the ops core."""

from __future__ import annotations

from crime_research_kit._runtime.adapters.ops import case, sources
from crime_research_kit._runtime.adapters.ops.result import OpResult
from crime_research_kit._runtime.adapters.ops.runner import CrkRunner
from crime_research_kit._runtime.pipeline.agents.source_lanes import infer_source_lanes
from crime_research_kit._runtime.pipeline.graph.state import GraphState

case_ops = case
source_ops = sources


def infer_lanes_node(state: GraphState) -> GraphState:
    lanes = infer_source_lanes(state.get("subject"), state.get("lanes") or [])
    return {"lanes": lanes, "status": "lanes_inferred"}


def init_case_node(runner: CrkRunner):
    def node(state: GraphState) -> GraphState:
        result = case_ops.init_case(runner, required_case_dir(state), state.get("title"))
        return merge_result(state, result, "case_initialized")

    return node


def plan_public_records_node(runner: CrkRunner):
    def node(state: GraphState) -> GraphState:
        subject = state.get("subject")
        if not subject:
            return {
                "status": "source_plan_skipped",
                "errors": append_error(state, "No subject provided for source planning."),
            }
        result = source_ops.plan_public_records(runner, required_case_dir(state), subject, state.get("lanes") or [])
        return merge_result(state, result, "source_plan_ready")

    return node


def merge_result(state: GraphState, result: OpResult, success_status: str) -> GraphState:
    return {
        "planned_commands": [*(state.get("planned_commands") or []), result.command],
        "tool_results": [*(state.get("tool_results") or []), result.to_dict()],
        "errors": [*(state.get("errors") or []), *result.errors],
        "status": success_status if result.ok else "error",
    }


def append_error(state: GraphState, message: str) -> list[str]:
    return [*(state.get("errors") or []), message]


def required_case_dir(state: GraphState) -> str:
    case_dir = state.get("case_dir")
    if not case_dir:
        raise ValueError("case_dir is required")
    return case_dir
