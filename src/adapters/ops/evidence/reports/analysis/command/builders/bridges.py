"""Cluster bridge data products for analysis chart exports."""

from __future__ import annotations

from itertools import combinations
from typing import Any

from core.casefile import slugify

from adapters.ops.evidence.reports.analysis.classifiers import (
    boundary_signal,
    readiness_label,
    source_grade_counts,
    weakest_status,
)
from adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from adapters.ops.evidence.reports.analysis.paths import audit_bridge_class, classify_bridge_path, shortest_analysis_path
from adapters.ops.evidence.reports.analysis.relationships import relationship_class
from adapters.ops.evidence.reports.common import entity_display, parse_cell_list


def build_cluster_bridges(ctx: AnalysisContext) -> dict[str, Any]:
    sankey_nodes: list[dict[str, Any]] = []
    for cluster_id in ctx.cluster_ids:
        members = sorted(ctx.cluster_members[cluster_id], key=lambda person_id: entity_display(ctx.people_by_id.get(person_id)))
        summary = ctx.cluster_summary.get(cluster_id, {})
        sankey_nodes.append({
            "cluster_id": cluster_id,
            "cluster_label": ctx.cluster_labels.get(cluster_id, summary.get("label") or summary.get("members") or cluster_id),
            "member_entity_ids": members,
            "member_names": [entity_display(ctx.people_by_id.get(person_id)) for person_id in members],
            "size": len(members),
            "mean_kde_density": summary.get("mean_kde_density", ""),
            "internal_edge_weight": summary.get("internal_edge_weight", ""),
            "boundary_edge_weight": summary.get("boundary_edge_weight", ""),
            "notes": "cluster from people_clusters.csv" if ctx.cluster_summary else "fallback one-person cluster",
        })

    cluster_bridge_rows: list[dict[str, Any]] = []
    cluster_bridge_links: list[dict[str, Any]] = []
    bridge_segment_rows: list[dict[str, Any]] = []
    edge_load: dict[str, dict[str, Any]] = {}
    audit_by_pair = {(row["src_cluster"], row["dst_cluster"]): row for row in ctx.audit_bridges}
    bridge_pairs = list(audit_by_pair) if audit_by_pair else list(combinations(ctx.cluster_ids, 2))
    for left, right in bridge_pairs:
        steps = shortest_analysis_path(ctx.graph, ctx.cluster_members[left], ctx.cluster_members[right])
        audit_row = audit_by_pair.get((left, right), {})
        if steps is None and not audit_row:
            continue
        steps = steps or []
        statuses = sorted({str(step[2].get("status", "")) for step in steps})
        relationship_classes = sorted({
            relationship_class(step[2], str(step[2].get("edge_type", "relationship")), packs=ctx.packs)
            for step in steps
        })
        source_ids = sorted({sid for step in steps for sid in parse_cell_list(step[2].get("source_ids"))})
        if audit_row.get("audit_source_ids"):
            source_ids = sorted(set(source_ids) | set(parse_cell_list(audit_row.get("audit_source_ids"))))
        claim_ids = sorted({cid for step in steps for cid in parse_cell_list(step[2].get("claim_ids"))})
        source_rows = ctx.source_rows_for_ids(source_ids)
        boundary_claim_ids = sorted(
            claim_id for claim_id in claim_ids
            if claim_id in ctx.claim_by_id and boundary_signal(ctx.claim_by_id[claim_id])
        )
        bridge_class = (
            audit_bridge_class(str(audit_row.get("capacity", "")))
            if audit_row
            else classify_bridge_path(steps, ctx.graph_meta, packs=ctx.packs)
        )
        path_text = ctx.path_label(steps) or str(audit_row.get("audit_path", ""))
        public_export = all(step[2].get("public_export", True) is not False for step in steps) if steps else bool(audit_row)
        is_lead_bridge = "lead" in " ".join([str(audit_row.get("capacity", "")), str(audit_row.get("boundary_text", "")), bridge_class]).lower()
        row = {
            "bridge_id": audit_row.get("bridge_id") or f"B_{left}_{right}_{slugify(bridge_class, 32).upper()}",
            "src_cluster": left,
            "dst_cluster": right,
            "src_cluster_label": ctx.cluster_labels.get(left, left),
            "dst_cluster_label": ctx.cluster_labels.get(right, right),
            "bridge_class": bridge_class,
            "relationship_classes": relationship_classes,
            "hops": len(steps),
            "path": path_text,
            "statuses": statuses,
            "source_ids": source_ids,
            "claim_ids": claim_ids,
            "boundary_claim_ids": boundary_claim_ids,
            "boundary_text": audit_row.get("boundary_text", ""),
            "source_grade_counts": source_grade_counts(source_rows),
            "public_readiness": "lead_or_disputed"
            if is_lead_bridge
            else readiness_label(
                {"status": weakest_status(statuses, packs=ctx.packs) or "single_source", "public_export": public_export},
                source_rows,
            ),
            "public_export": public_export,
            "notes": audit_row.get("capacity", ""),
        }
        cluster_bridge_rows.append(row)
        cluster_bridge_links.append(row)
        _append_bridge_segments(ctx, steps, row, bridge_class, bridge_segment_rows, edge_load)
    return {
        "sankey_nodes": sankey_nodes,
        "cluster_bridge_rows": cluster_bridge_rows,
        "cluster_bridge_links": cluster_bridge_links,
        "bridge_segment_rows": bridge_segment_rows,
        "edge_load": edge_load,
    }


def _append_bridge_segments(
    ctx: AnalysisContext,
    steps: list[tuple[str, str, dict[str, Any]]],
    row: dict[str, Any],
    bridge_class: str,
    bridge_segment_rows: list[dict[str, Any]],
    edge_load: dict[str, dict[str, Any]],
) -> None:
    for src, dst, edge in steps:
        record_id = str(edge.get("record_id", ""))
        if not record_id:
            continue
        bridge_segment_rows.append({
            "bridge_id": row["bridge_id"],
            "segment_index": len([segment for segment in bridge_segment_rows if segment.get("bridge_id") == row["bridge_id"]]) + 1,
            "src_id": src,
            "src_label": ctx.node_label(src),
            "dst_id": dst,
            "dst_label": ctx.node_label(dst),
            "record_type": edge.get("edge_type", ""),
            "record_id": record_id,
            "relation_type": edge.get("relation_type", ""),
            "relationship_class": edge.get("relationship_class")
            or relationship_class(edge, str(edge.get("edge_type", "relationship")), packs=ctx.packs),
            "status": edge.get("status", ""),
            "confidence": edge.get("confidence", ""),
            "source_ids": parse_cell_list(edge.get("source_ids")),
            "claim_ids": parse_cell_list(edge.get("claim_ids")),
            "public_export": edge.get("public_export", True),
            "guardrail_note": "lead/category/context edge; do not read as direct personal tie"
            if classify_bridge_path([(src, dst, edge)], ctx.graph_meta, packs=ctx.packs) != "direct_or_near_direct"
            else "",
        })
        load = edge_load.setdefault(record_id, {
            "record_id": record_id,
            "edge_type": edge.get("edge_type", ""),
            "relation_type": edge.get("relation_type", ""),
            "relationship_class": edge.get("relationship_class")
            or relationship_class(edge, str(edge.get("edge_type", "relationship")), packs=ctx.packs),
            "status": edge.get("status", ""),
            "source_ids": set(),
            "claim_ids": set(),
            "load_bearing_score": 0,
            "bridge_classes": set(),
            "example_path": ctx.path_label(steps),
        })
        load["load_bearing_score"] += 1
        load["bridge_classes"].add(bridge_class)
        load.setdefault("relationship_classes", set()).add(
            edge.get("relationship_class")
            or relationship_class(edge, str(edge.get("edge_type", "relationship")), packs=ctx.packs)
        )
        load["source_ids"].update(parse_cell_list(edge.get("source_ids")))
        load["claim_ids"].update(parse_cell_list(edge.get("claim_ids")))
