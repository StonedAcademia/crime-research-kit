"""Application service boundary for case-builder workflow runs."""

from __future__ import annotations

from typing import Any, Literal, Sequence

from adapters.ops.runner import CrkRunner
from core.models.state import CaseBuilderState
from pipeline.graph.persistence.checkpoint import case_checkpointer
from pipeline.graph.runner import build_case_builder_graph, langgraph_available, run_sequential

RunnerName = Literal["auto", "langgraph", "sequential"]
LANGGRAPH_HINT = "LangGraph is not installed. Install with `pip install -e '.[agentic]'`."


def _model_factory(llm_enabled: bool, model_spec: str | None = None):
    if not llm_enabled:
        return None
    from adapters.interfaces.llm.provider import get_chat_model

    def factory(spec: str | None = None):
        return get_chat_model(spec or model_spec)

    return factory


def run_case_builder(
    state: CaseBuilderState,
    *,
    execute: bool = False,
    runner: RunnerName = "auto",
    checkpoint: bool = False,
    model_spec: str | None = None,
    qdrant_url: str | None = None,
    embed_model: str | None = None,
) -> dict[str, Any]:
    """Run a case-builder plan and return serializable state.

    Dry runs produce the exact CRK commands the app would execute. Executed
    runs still stop at human review gates before canonical import or export.
    """
    crk = CrkRunner(dry_run=not execute)
    state.qdrant_url = qdrant_url or state.qdrant_url
    state.embed_model = embed_model or state.embed_model
    model_factory = _model_factory(state.llm_enabled, model_spec)
    use_langgraph = runner in {"auto", "langgraph"} and langgraph_available()
    if runner == "langgraph" and not langgraph_available():
        raise RuntimeError(LANGGRAPH_HINT)
    if not use_langgraph:
        if checkpoint:
            raise RuntimeError("Checkpointing requires the langgraph runner.")
        return run_sequential(state, crk, model_factory=model_factory)

    payload = state.to_dict()
    if not checkpoint:
        graph = build_case_builder_graph(crk, model_factory=model_factory)
        result = dict(graph.invoke(payload))
        result["runner"] = "langgraph"
        return result

    graph = build_case_builder_graph(
        crk,
        checkpointer=case_checkpointer(state.case_dir),
        use_interrupt=True,
        model_factory=model_factory,
    )
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
    llm: bool = False,
    model_spec: str | None = None,
    qdrant_url: str | None = None,
    embed_model: str | None = None,
) -> dict[str, Any]:
    """Resume a checkpointed run with human review decisions."""
    if not langgraph_available():
        raise RuntimeError(LANGGRAPH_HINT)
    from langgraph.types import Command

    crk = CrkRunner(dry_run=not execute)
    graph = build_case_builder_graph(
        crk,
        checkpointer=case_checkpointer(case_dir),
        use_interrupt=True,
        model_factory=_model_factory(llm, model_spec),
    )
    config = {"configurable": {"thread_id": thread_id}}
    payload = {
        "approved_packets": list(approved_packets),
        "rejected_packets": [dict(item) for item in rejected_packets],
        "export_approved": export_approved,
    }
    state_update = {k: v for k, v in {"qdrant_url": qdrant_url, "embed_model": embed_model}.items() if v is not None}
    result = dict(graph.invoke(Command(resume=payload, update=state_update or None), config))
    return _annotate(result, graph, config, thread_id)


def _annotate(result: dict[str, Any], graph: Any, config: dict[str, Any], thread_id: str) -> dict[str, Any]:
    snapshot = graph.get_state(config)
    result["paused_before"] = list(snapshot.next)
    result["thread_id"] = thread_id
    result["runner"] = "langgraph"
    return result
