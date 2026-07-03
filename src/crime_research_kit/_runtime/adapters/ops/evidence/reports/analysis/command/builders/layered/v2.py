"""Layered graph v2 products for analysis exports."""

from __future__ import annotations

from typing import Any

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.classifiers import (
    best_grade,
    boundary_signal,
    readiness_label,
    source_grade_counts,
    source_grade_score,
    status_score,
)
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.layered.layers import build_layered_v2_layers
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.layered.vocab import layer_order_map
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.paths import classify_bridge_path
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.relationships import relation_family
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.vocabulary import VocabPacks
from crime_research_kit._runtime.adapters.ops.evidence.reports.common import parse_cell_list


def build_layered_v2(
    ctx: AnalysisContext,
    layered_nodes: list[dict[str, Any]],
    layered_edges: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    event_record_by_node = {"EVENT:" + str(event.get("event_id")): event for event in ctx.events}
    degree_by_node: dict[str, int] = {}
    for edge in layered_edges:
        degree_by_node[str(edge.get("src_id", ""))] = degree_by_node.get(str(edge.get("src_id", "")), 0) + 1
        degree_by_node[str(edge.get("dst_id", ""))] = degree_by_node.get(str(edge.get("dst_id", "")), 0) + 1
    layered_v2_nodes = _layered_v2_nodes(ctx, layered_nodes, event_record_by_node, degree_by_node)
    layered_v2_edges = _layered_v2_edges(ctx, layered_edges)
    layered_v2_layers = build_layered_v2_layers(layered_v2_nodes, layered_v2_edges, packs=ctx.packs)
    return {
        "layered_v2_nodes": layered_v2_nodes,
        "layered_v2_edges": layered_v2_edges,
        "layered_v2_layers": layered_v2_layers,
    }


def _node_evidence_state(
    record: dict[str, Any],
    source_rows: list[dict[str, Any]],
    packs: VocabPacks,
) -> str:
    if record.get("public_export", True) is False:
        return "internal_only"
    status = str(record.get("status", ""))
    if status == "candidate":
        return "candidate_or_identity_review"
    if not source_rows:
        return "unsourced_context"
    grade = best_grade(source_rows, packs=packs)
    if grade in {"A", "B"}:
        return "documented_source"
    return "source_note_required"


def _layered_v2_nodes(
    ctx: AnalysisContext,
    layered_nodes: list[dict[str, Any]],
    event_record_by_node: dict[str, dict[str, Any]],
    degree_by_node: dict[str, int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    order_map = layer_order_map(ctx.packs)
    for row in layered_nodes:
        node_id = str(row.get("node_id", ""))
        record = ctx.entity_by_id.get(node_id) or event_record_by_node.get(node_id) or {}
        source_ids = parse_cell_list(record.get("source_ids"))
        claim_ids = parse_cell_list(record.get("claim_ids"))
        node_sources = ctx.source_rows_for_ids(source_ids)
        readiness = readiness_label(record, node_sources) if record else "review_needed"
        layer = str(row.get("layer") or "entity")
        evidence_state = _node_evidence_state(record, node_sources, ctx.packs)
        boundary = boundary_signal(record) if record else False
        rows.append({
            "node_id": node_id,
            "label": row.get("label", ""),
            "layer": layer,
            "layer_order": order_map.get(layer, 99),
            "cluster_id": row.get("cluster_id", ""),
            "status": record.get("status", row.get("status", "")),
            "degree": degree_by_node.get(node_id, 0),
            "source_count": len(source_ids),
            "independent_source_count": ctx.independent_source_count(node_sources),
            "best_source_grade": best_grade(node_sources, packs=ctx.packs),
            "source_grade_counts": source_grade_counts(node_sources),
            "claim_count": len(claim_ids),
            "evidence_state": evidence_state,
            "readiness": readiness,
            "boundary_flag": boundary,
            "public_export": record.get("public_export", row.get("public_export", True)),
            "caveat": "Boundary/context node; inspect source chain before narration." if boundary or evidence_state in {"candidate_or_identity_review", "unsourced_context"} else "",
        })
    return rows


def _caveat_for_edge(edge: dict[str, Any], source_rows: list[dict[str, Any]], boundary_claim_ids: list[str], bridge_class: str) -> str:
    status = str(edge.get("status", ""))
    edge_class = str(edge.get("relationship_class", ""))
    if edge.get("public_export", True) is False:
        return "Internal-only edge; do not use in public narrative without review."
    if edge_class == "hypothesis_requires_more_sources" or status == "unverified":
        return "Hypothesis/lead; needs more independent sources."
    if edge_class == "contested_overlap" or status == "disputed" or boundary_claim_ids:
        return "Contested or boundary-marked edge; narrate with the dispute."
    if bridge_class not in {"direct_or_near_direct", "documented_successor_bridge"}:
        return "Context/category/method bridge; not a direct personal tie."
    if len(source_rows) <= 1 or status == "single_source":
        return "Single-source edge; verify before public narrative use."
    return ""


def _layered_v2_edges(ctx: AnalysisContext, layered_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, edge in enumerate(layered_edges, start=1):
        source_ids = set(parse_cell_list(edge.get("source_ids")))
        claim_ids = parse_cell_list(edge.get("claim_ids"))
        boundary_claim_ids: list[str] = []
        for claim_id in claim_ids:
            claim = ctx.claim_by_id.get(claim_id)
            if not claim:
                continue
            source_ids.update(parse_cell_list(claim.get("source_ids")))
            if boundary_signal(claim):
                boundary_claim_ids.append(claim_id)
        edge_sources = ctx.source_rows_for_ids(sorted(source_ids))
        src_id = str(edge.get("src_id", ""))
        dst_id = str(edge.get("dst_id", ""))
        graph_edge = {
            "record_id": edge.get("edge_id") or edge.get("record_id") or f"LKG2_{idx}",
            "edge_type": edge.get("edge_type", ""),
            "relation_type": edge.get("relation_type", ""),
            "relationship_class": edge.get("relationship_class", ""),
            "status": edge.get("status", ""),
            "source_ids": sorted(source_ids),
            "claim_ids": claim_ids,
            "confidence": edge.get("confidence", ""),
            "notes": "",
            "public_export": edge.get("public_export", True),
        }
        bridge_class = classify_bridge_path([(src_id, dst_id, graph_edge)], ctx.graph_meta, packs=ctx.packs)
        readiness = readiness_label(graph_edge, edge_sources)
        evidence_weight = round(
            (status_score(str(edge.get("status", "")), packs=ctx.packs) or 0.35)
            * max(0.35, source_grade_score(edge_sources, packs=ctx.packs))
            * (1.0 + min(4, len(edge_sources)) * 0.12),
            3,
        )
        caveat = _caveat_for_edge(graph_edge, edge_sources, boundary_claim_ids, bridge_class)
        rows.append({
            "edge_id": graph_edge["record_id"],
            "src_id": src_id,
            "dst_id": dst_id,
            "src_label": edge.get("src_label", ""),
            "dst_label": edge.get("dst_label", ""),
            "src_layer": ctx.graph_meta.get(src_id, {}).get("layer", ""),
            "dst_layer": ctx.graph_meta.get(dst_id, {}).get("layer", ""),
            "edge_type": edge.get("edge_type", ""),
            "relation_type": edge.get("relation_type", ""),
            "relationship_class": edge.get("relationship_class", ""),
            "relation_family": relation_family(
                str(edge.get("relation_type", "")),
                str(edge.get("edge_type", "")),
                packs=ctx.packs,
            ),
            "bridge_class": bridge_class,
            "status": edge.get("status", ""),
            "confidence": edge.get("confidence", ""),
            "evidence_weight": evidence_weight,
            "source_count": len(edge_sources),
            "independent_source_count": ctx.independent_source_count(edge_sources),
            "best_source_grade": best_grade(edge_sources, packs=ctx.packs),
            "source_grade_counts": source_grade_counts(edge_sources),
            "claim_ids": claim_ids,
            "source_ids": sorted(source_ids),
            "boundary_claim_ids": sorted(boundary_claim_ids),
            "readiness": readiness,
            "boundary_flag": bool(boundary_claim_ids) or boundary_signal(graph_edge),
            "public_export": edge.get("public_export", True),
            "caveat": caveat,
        })
    return rows
