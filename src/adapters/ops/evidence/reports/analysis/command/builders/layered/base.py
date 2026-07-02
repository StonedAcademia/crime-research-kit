"""Base layered graph products for analysis exports."""

from __future__ import annotations

from typing import Any

from adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from adapters.ops.evidence.reports.analysis.relationships import relationship_class
from adapters.ops.evidence.reports.common import parse_cell_list


def build_layered_base(ctx: AnalysisContext) -> dict[str, list[dict[str, Any]]]:
    layered_nodes: list[dict[str, Any]] = []
    for node_id, meta in sorted(ctx.graph_meta.items(), key=lambda item: (item[1].get("layer", ""), item[1].get("label", ""))):
        source_ids = parse_cell_list(ctx.entity_by_id.get(node_id, {}).get("source_ids")) if node_id in ctx.entity_by_id else []
        layered_nodes.append({
            "node_id": node_id,
            "label": meta.get("label", ""),
            "layer": meta.get("layer", ""),
            "cluster_id": meta.get("cluster_id", ""),
            "status": ctx.entity_by_id.get(node_id, {}).get("status", ""),
            "source_count": len(source_ids),
            "public_export": ctx.entity_by_id.get(node_id, {}).get("public_export", True),
        })
    seen_edges: set[tuple[str, str, str]] = set()
    layered_edges: list[dict[str, Any]] = []
    for src, edges in ctx.graph.items():
        for dst, edge in edges:
            key = tuple(sorted([src, dst]) + [str(edge.get("record_id", ""))])
            if key in seen_edges:
                continue
            seen_edges.add(key)
            layered_edges.append({
                "src_id": src,
                "dst_id": dst,
                "src_label": ctx.node_label(src),
                "dst_label": ctx.node_label(dst),
                "edge_type": edge.get("edge_type", ""),
                "relation_type": edge.get("relation_type", ""),
                "relationship_class": edge.get("relationship_class") or relationship_class(edge, str(edge.get("edge_type", "relationship"))),
                "status": edge.get("status", ""),
                "confidence": edge.get("confidence", ""),
                "source_count": len(parse_cell_list(edge.get("source_ids"))),
                "source_ids": parse_cell_list(edge.get("source_ids")),
                "claim_ids": parse_cell_list(edge.get("claim_ids")),
                "public_export": edge.get("public_export", True),
            })
    return {"layered_nodes": layered_nodes, "layered_edges": layered_edges}
