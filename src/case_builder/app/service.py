"""Application service boundary for case-builder workflow runs."""

from __future__ import annotations

from typing import Any, Literal

from ..graph.runner import build_case_builder_graph, langgraph_available, run_sequential
from ..models.state import CaseBuilderState
from ..ops.runner import TrcrRunner

RunnerName = Literal["auto", "langgraph", "sequential"]


def run_case_builder(
    state: CaseBuilderState,
    *,
    execute: bool = False,
    runner: RunnerName = "auto",
) -> dict[str, Any]:
    """Run a case-builder plan and return serializable state.

    Dry runs produce the exact TRCR commands the app would execute. Executed
    runs still stop at a human review gate before any narrative use.
    """
    trcr = TrcrRunner(dry_run=not execute)
    if runner in {"auto", "langgraph"} and langgraph_available():
        graph = build_case_builder_graph(trcr)
        result = graph.invoke(state.to_dict())
        result["runner"] = "langgraph"
        return result
    if runner == "langgraph":
        raise RuntimeError("LangGraph is not installed. Install with `pip install -e '.[agentic]'`.")
    return run_sequential(state, trcr)
