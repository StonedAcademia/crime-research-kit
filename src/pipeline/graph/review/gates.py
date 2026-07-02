"""Human review gates: interrupt-based under LangGraph, terminal otherwise."""

from __future__ import annotations

from pipeline.graph.state import GraphState

WAITING = {"review_required": True, "status": "waiting_for_human_review"}


def packet_review_gate_node(use_interrupt: bool):
    def node(state: GraphState) -> GraphState:
        if state.get("approved_packets"):
            return {"status": "packets_approved", "review_required": False}
        if use_interrupt:
            from langgraph.types import interrupt

            decision = interrupt(
                {
                    "action": "review_packets",
                    "case_dir": state.get("case_dir"),
                    "packets": state.get("packets") or [],
                }
            )
            approved = list(decision.get("approved_packets") or [])
            return {
                "approved_packets": approved,
                "rejected_packets": list(decision.get("rejected_packets") or []),
                "review_required": False,
                "status": "packets_approved" if approved else "packets_rejected",
            }
        return dict(WAITING)

    return node


def export_review_gate_node(use_interrupt: bool):
    def node(state: GraphState) -> GraphState:
        if state.get("export_approved"):
            return {"status": "export_approved", "review_required": False}
        if use_interrupt:
            from langgraph.types import interrupt

            decision = interrupt({"action": "review_export", "case_dir": state.get("case_dir")})
            approved = bool(decision.get("export_approved"))
            return {
                "export_approved": approved,
                "review_required": not approved,
                "status": "export_approved" if approved else "waiting_for_human_review",
            }
        return dict(WAITING)

    return node
