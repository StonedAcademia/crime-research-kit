"""Graph construction plus deterministic local execution fallback."""

from __future__ import annotations

from ..models.state import CaseBuilderState
from ..ops.runner import TrcrRunner
from .nodes import infer_lanes_node, init_case_node, plan_public_records_node, review_gate_node
from .state import GraphState


def run_sequential(state: CaseBuilderState, runner: TrcrRunner) -> dict[str, object]:
    current: GraphState = state.to_dict()
    for node in (infer_lanes_node, init_case_node(runner), plan_public_records_node(runner), review_gate_node):
        current.update(node(current))
    current["runner"] = "sequential"
    return dict(current)


def build_case_builder_graph(runner: TrcrRunner):
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError("LangGraph is not installed. Install with `pip install -e '.[agentic]'`.") from exc

    graph = StateGraph(GraphState)
    graph.add_node("infer_lanes", infer_lanes_node)
    graph.add_node("init_case", init_case_node(runner))
    graph.add_node("plan_public_records", plan_public_records_node(runner))
    graph.add_node("review_gate", review_gate_node)
    graph.add_edge(START, "infer_lanes")
    graph.add_edge("infer_lanes", "init_case")
    graph.add_edge("init_case", "plan_public_records")
    graph.add_edge("plan_public_records", "review_gate")
    graph.add_edge("review_gate", END)
    return graph.compile()


def langgraph_available() -> bool:
    try:
        import langgraph  # noqa: F401
    except ImportError:
        return False
    return True
