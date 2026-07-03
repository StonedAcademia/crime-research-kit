"""Graph construction plus deterministic local execution fallback."""

from __future__ import annotations

from crime_research_kit._runtime.adapters.ops.runner import CrkRunner
from crime_research_kit._runtime.core.models.state import CaseBuilderState
from crime_research_kit._runtime.pipeline.graph.nodes.base import infer_lanes_node, init_case_node, plan_public_records_node
from crime_research_kit._runtime.pipeline.graph.nodes.llm import fill_packets_node, readiness_brief_node, suggest_lanes_node
from crime_research_kit._runtime.pipeline.graph.nodes.pipeline import (
    draft_packets_node,
    export_bundle_node,
    import_and_validate_node,
    index_case_node,
    parse_or_ocr_node,
    readiness_audit_node,
    source_capture_node,
)
from crime_research_kit._runtime.pipeline.graph.review.gates import export_review_gate_node, packet_review_gate_node
from crime_research_kit._runtime.pipeline.graph.state import GraphState

GATE_TARGETS = {"packet_review_gate": "import_and_validate", "export_review_gate": "export_bundle"}
STOP_STATUSES = {"waiting_for_human_review", "packets_rejected"}


def pipeline_nodes_list(runner: CrkRunner, *, use_interrupt: bool, model_factory=None):
    return [
        ("infer_lanes", infer_lanes_node),
        ("suggest_lanes", suggest_lanes_node(runner, model_factory)),
        ("init_case", init_case_node(runner)),
        ("plan_public_records", plan_public_records_node(runner)),
        ("source_capture", source_capture_node(runner)),
        ("parse_or_ocr", parse_or_ocr_node(runner)),
        ("draft_packets", draft_packets_node(runner)),
        ("fill_packets", fill_packets_node(runner, model_factory)),
        ("packet_review_gate", packet_review_gate_node(use_interrupt)),
        ("import_and_validate", import_and_validate_node(runner)),
        ("index_case", index_case_node(runner)),
        ("readiness_audit", readiness_audit_node(runner)),
        ("readiness_brief", readiness_brief_node(runner, model_factory)),
        ("export_review_gate", export_review_gate_node(use_interrupt)),
        ("export_bundle", export_bundle_node(runner)),
    ]


def run_sequential(state: CaseBuilderState, runner: CrkRunner, *, model_factory=None) -> dict[str, object]:
    current: GraphState = state.to_dict()
    for _name, node in pipeline_nodes_list(runner, use_interrupt=False, model_factory=model_factory):
        current.update(node(current))
        if current.get("status") in STOP_STATUSES:
            break
    current["runner"] = "sequential"
    return dict(current)


def build_case_builder_graph(runner: CrkRunner, *, checkpointer=None, use_interrupt: bool = False, model_factory=None):
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError("LangGraph is not installed. Install with `pip install -e '.[agentic]'`.") from exc

    nodes = pipeline_nodes_list(runner, use_interrupt=use_interrupt, model_factory=model_factory)
    graph = StateGraph(GraphState)
    for name, node in nodes:
        graph.add_node(name, node)
    names = [name for name, _ in nodes]
    graph.add_edge(START, names[0])
    for previous, upcoming in zip(names, names[1:]):
        if previous in GATE_TARGETS:
            continue
        graph.add_edge(previous, upcoming)
    for gate, target in GATE_TARGETS.items():
        graph.add_conditional_edges(gate, _gate_router(target, END))
    graph.add_edge(names[-1], END)
    return graph.compile(checkpointer=checkpointer)


def _gate_router(target: str, end):
    def route(state: GraphState):
        return end if state.get("status") in STOP_STATUSES else target

    return route


def langgraph_available() -> bool:
    try:
        import langgraph  # noqa: F401
    except ImportError:
        return False
    return True
