"""Hub-aware clustered visual products for case exports."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.clustered.rules import (
    cluster_for,
    edge_visibility,
    edge_weight,
    facet_types,
    hub_role,
    semantic_facets,
)
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.clustered.sources import (
    cluster_timeline,
    source_subproject_edges,
    subproject_index,
    subproject_matrix,
)
from crime_research_kit._runtime.adapters.ops.evidence.reports.common import parse_cell_list


def build_clustered_visual_products(ctx: AnalysisContext, products: dict[str, Any]) -> dict[str, Any]:
    nodes = [dict(row) for row in products["relationship_network_nodes"]]
    edges = [dict(row) for row in products["relationship_network_edges"]]
    threshold = _degree_threshold(nodes)
    node_by_id = _augment_nodes(nodes, threshold)
    _augment_edges(edges, node_by_id)
    subprojects = subproject_index(ctx, node_by_id)
    matrix = subproject_matrix(subprojects)
    timeline = cluster_timeline(ctx)
    overview = _cluster_overview(nodes, edges, matrix, timeline)
    return {
        "relationship_network_nodes": nodes,
        "relationship_network_edges": edges,
        "cluster_overview": overview,
        "cluster_detail_edges": [edge for edge in edges if edge.get("edge_visibility") != "hidden_by_default"],
        "source_subproject_edges": source_subproject_edges(ctx, subprojects),
        "subproject_matrix": matrix,
        "cluster_timeline": timeline,
        "hub_nodes": [node for node in nodes if node.get("hub_role")],
        "facet_counts": _facet_counts(edges),
        "cluster_policy": {
            "hub_degree_threshold": threshold,
            "method": "deterministic structural rules using subproject ranges and document/context packets; activity keywords remain filter facets",
            "default_edge_visibility": "default edges only; hub and omnibus-context edges are kept as context filters",
        },
    }


def _augment_nodes(nodes: list[dict[str, Any]], threshold: int) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        cid, label = cluster_for(str(node.get("layer", "")), node.get("node_id"), node.get("label"))
        role = hub_role(node, threshold)
        node.update({
            "cluster_id": cid,
            "cluster_label": label,
            "facet_types": ";".join(semantic_facets(node.get("node_id"), node.get("label"))),
            "hub_role": role,
            "node_visibility": "collapsed_by_default" if role else "default",
        })
        by_id[str(node.get("node_id"))] = node
    return by_id


def _augment_edges(edges: list[dict[str, Any]], node_by_id: dict[str, dict[str, Any]]) -> None:
    for edge in edges:
        src = node_by_id.get(str(edge.get("src_id")), {})
        dst = node_by_id.get(str(edge.get("dst_id")), {})
        src_hub = bool(src.get("hub_role"))
        dst_hub = bool(dst.get("hub_role"))
        weight = edge_weight(edge, src_hub, dst_hub)
        visibility = edge_visibility(edge, weight, src_hub, dst_hub)
        src_cluster = str(src.get("cluster_id", "ENTITY_CONTEXT"))
        dst_cluster = str(dst.get("cluster_id", "ENTITY_CONTEXT"))
        cid = src_cluster if src_cluster == dst_cluster else _non_context_cluster(src_cluster, dst_cluster)
        edge.update({
            "src_cluster_id": src_cluster,
            "src_cluster_label": src.get("cluster_label", ""),
            "dst_cluster_id": dst_cluster,
            "dst_cluster_label": dst.get("cluster_label", ""),
            "cluster_id": cid,
            "cluster_label": src.get("cluster_label") if cid == src_cluster else dst.get("cluster_label") if cid == dst_cluster else "Intercluster bridge",
            "hub_role": src.get("hub_role") or dst.get("hub_role") or "",
            "edge_weight": weight,
            "edge_visibility": visibility,
            "facet_types": facet_types(edge),
        })


def _cluster_overview(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], matrix: list[dict[str, Any]], timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"source_ids": set(), "claim_ids": set(), "facets": Counter(), "readiness": Counter()})
    for node in nodes:
        item = grouped[str(node.get("cluster_id"))]
        item["cluster_label"] = node.get("cluster_label", "")
        item["node_count"] = item.get("node_count", 0) + 1
        item["hub_node_count"] = item.get("hub_node_count", 0) + int(bool(node.get("hub_role")))
        item["source_ids"].update(parse_cell_list(node.get("source_ids")))
        item["claim_ids"].update(parse_cell_list(node.get("claim_ids")))
        item["facets"].update(parse_cell_list(node.get("facet_types")))
        item["readiness"][str(node.get("readiness", "review_needed"))] += 1
    for edge in edges:
        item = grouped[str(edge.get("cluster_id"))]
        item["cluster_label"] = edge.get("cluster_label", item.get("cluster_label", ""))
        item["edge_count"] = item.get("edge_count", 0) + 1
        item["visible_edge_count"] = item.get("visible_edge_count", 0) + int(edge.get("edge_visibility") == "default")
        item["source_ids"].update(parse_cell_list(edge.get("source_ids")))
        item["claim_ids"].update(parse_cell_list(edge.get("claim_ids")))
        item["facets"].update(parse_cell_list(edge.get("facet_types")))
    for row in matrix:
        item = grouped[str(row.get("cluster_id"))]
        item["cluster_label"] = row.get("cluster_label", item.get("cluster_label", ""))
        item["subproject_count"] = item.get("subproject_count", 0) + 1
        item["facets"].update(parse_cell_list(row.get("facet_types")))
    for row in timeline:
        item = grouped[str(row.get("cluster_id"))]
        item["event_count"] = item.get("event_count", 0) + 1
        item.setdefault("dates", []).append(str(row.get("start_date", "")))
    overview = []
    for cid, item in grouped.items():
        dates = sorted([date for date in item.get("dates", []) if date])
        node_count = item.get("node_count", 0)
        edge_count = item.get("edge_count", 0)
        visible_edge_count = item.get("visible_edge_count", 0)
        event_count = item.get("event_count", 0)
        source_count = len(item["source_ids"])
        claim_count = len(item["claim_ids"])
        evidence_footprint_score = node_count + edge_count + claim_count + source_count + event_count
        overview.append({
            "cluster_id": cid,
            "cluster_label": item.get("cluster_label") or cid,
            "node_count": node_count,
            "record_count": node_count,
            "edge_count": edge_count,
            "relationship_count": edge_count,
            "visible_edge_count": visible_edge_count,
            "default_relationship_count": visible_edge_count,
            "hub_node_count": item.get("hub_node_count", 0),
            "subproject_count": item.get("subproject_count", 0),
            "event_count": event_count,
            "source_count": source_count,
            "claim_count": claim_count,
            "evidence_footprint_score": evidence_footprint_score,
            "top_facets": ";".join(name for name, _ in item["facets"].most_common(4)),
            "readiness": ";".join(f"{name}:{count}" for name, count in sorted(item["readiness"].items())),
            "first_date": dates[0] if dates else "",
            "last_date": dates[-1] if dates else "",
        })
    return sorted(overview, key=lambda row: (-int(row["evidence_footprint_score"]), -int(row["default_relationship_count"]), str(row["cluster_label"])))


def _facet_counts(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for edge in edges:
        counts.update(parse_cell_list(edge.get("facet_types")))
    return [{"facet_type": name, "count": count} for name, count in sorted(counts.items())]


def _degree_threshold(nodes: list[dict[str, Any]]) -> int:
    degrees = sorted(int(float(node.get("degree", 0) or 0)) for node in nodes)
    return max(12, degrees[int(len(degrees) * 0.95)] if degrees else 12)


def _non_context_cluster(left: str, right: str) -> str:
    for value in (left, right):
        if value not in {"PROGRAM_CONTEXT", "DOCUMENT_CONTEXT", "ENTITY_CONTEXT", "EVENT_CONTEXT"}:
            return value
    return "INTERCLUSTER"
