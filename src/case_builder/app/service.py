"""Application service boundary for case-builder workflow runs."""

from __future__ import annotations

from typing import Any, Literal, Sequence

from ..graph.checkpoint import case_checkpointer
from ..graph.runner import build_case_builder_graph, langgraph_available, run_sequential
from ..models.state import CaseBuilderState
from ..ops.runner import TrcrRunner

RunnerName = Literal["auto", "langgraph", "sequential"]
LANGGRAPH_HINT = "LangGraph is not installed. Install with `pip install -e '.[agentic]'`."


def run_case_builder(
    state: CaseBuilderState,
    *,
    execute: bool = False,
    runner: RunnerName = "auto",
    checkpoint: bool = False,
) -> dict[str, Any]:
    """Run a case-builder plan and return serializable state.

    Dry runs produce the exact TRCR commands the app would execute. Executed
    runs still stop at human review gates before canonical import or export.
    """
    trcr = TrcrRunner(dry_run=not execute)
    use_langgraph = runner in {"auto", "langgraph"} and langgraph_available()
    if runner == "langgraph" and not langgraph_available():
        raise RuntimeError(LANGGRAPH_HINT)
    if not use_langgraph:
        if checkpoint:
            raise RuntimeError("Checkpointing requires the langgraph runner.")
        return run_sequential(state, trcr)

    payload = state.to_dict()
    if not checkpoint:
        graph = build_case_builder_graph(trcr)
        result = dict(graph.invoke(payload))
        result["runner"] = "langgraph"
        return result

    graph = build_case_builder_graph(trcr, checkpointer=case_checkpointer(state.case_dir), use_interrupt=True)
    config = {"configurable": {"thread_id": payload["thread_id"]}}
    result = dict(graph.invoke(payload, config))
    return _annotate(result, graph, config, payload["thread_id"])


def resume_case_builder(
    case_dir: str,
    *,
    thread_id: str,
    approved_packets: Sequence[str] = (),
    rejected_packets: Sequence[dict[str, Any]] = (),
    export_approved: bool = False,
    execute: bool = False,
) -> dict[str, Any]:
    """Resume a checkpointed run with human review decisions."""
    if not langgraph_available():
        raise RuntimeError(LANGGRAPH_HINT)
    from langgraph.types import Command

    trcr = TrcrRunner(dry_run=not execute)
    graph = build_case_builder_graph(trcr, checkpointer=case_checkpointer(case_dir), use_interrupt=True)
    config = {"configurable": {"thread_id": thread_id}}
    payload = {
        "approved_packets": list(approved_packets),
        "rejected_packets": [dict(item) for item in rejected_packets],
        "export_approved": export_approved,
    }
    result = dict(graph.invoke(Command(resume=payload), config))
    return _annotate(result, graph, config, thread_id)


def _annotate(result: dict[str, Any], graph: Any, config: dict[str, Any], thread_id: str) -> dict[str, Any]:
    snapshot = graph.get_state(config)
    result["paused_before"] = list(snapshot.next)
    result["thread_id"] = thread_id
    result["runner"] = "langgraph"
    return result
