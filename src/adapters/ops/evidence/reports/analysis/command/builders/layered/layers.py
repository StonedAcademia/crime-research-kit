"""Layer summary rows for layered graph v2 exports."""

from __future__ import annotations

from typing import Any

from adapters.ops.evidence.reports.analysis.command.builders.layered.vocab import LAYER_ORDER_MAP
from adapters.ops.evidence.reports.weights import parse_float


def build_layered_v2_layers(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    layer_summary_map: dict[str, dict[str, Any]] = {}
    for node in nodes:
        layer = str(node.get("layer", "entity"))
        bucket = _layer_bucket(layer_summary_map, layer, node.get("layer_order", 99))
        bucket["node_count"] += 1
        bucket["public_node_count"] += 1 if node.get("public_export", True) is not False else 0
        bucket["internal_node_count"] += 1 if node.get("public_export", True) is False else 0
        bucket["candidate_node_count"] += 1 if str(node.get("status", "")) == "candidate" else 0
        bucket["source_count"] += int(node.get("source_count", 0) or 0)
    for edge in edges:
        for layer_key in ["src_layer", "dst_layer"]:
            layer = str(edge.get(layer_key) or "entity")
            bucket = _layer_bucket(layer_summary_map, layer, LAYER_ORDER_MAP.get(layer, 99))
            bucket["edge_count"] += 1
            bucket["public_edge_count"] += 1 if edge.get("public_export", True) is not False else 0
            bucket["lead_or_disputed_edge_count"] += 1 if str(edge.get("readiness", "")) == "lead_or_disputed" else 0
            bucket["public_ready_edge_count"] += 1 if str(edge.get("readiness", "")) == "public_ready" else 0
            status = str(edge.get("status", "") or "unknown")
            rel_class = str(edge.get("relationship_class", "") or "unknown")
            bucket["_statuses"][status] = bucket["_statuses"].get(status, 0) + 1
            bucket["_classes"][rel_class] = bucket["_classes"].get(rel_class, 0) + 1
    rows = []
    for row in sorted(layer_summary_map.values(), key=lambda item: (int(parse_float(item.get("layer_order"), 99)), str(item.get("layer", "")))):
        statuses = sorted(row.pop("_statuses").items(), key=lambda item: (-item[1], item[0]))
        classes = sorted(row.pop("_classes").items(), key=lambda item: (-item[1], item[0]))
        row["dominant_statuses"] = ";".join(f"{key}:{value}" for key, value in statuses[:5])
        row["dominant_relationship_classes"] = ";".join(f"{key}:{value}" for key, value in classes[:5])
        rows.append(row)
    return rows


def _layer_bucket(layer_summary_map: dict[str, dict[str, Any]], layer: str, order: Any) -> dict[str, Any]:
    return layer_summary_map.setdefault(layer, {
        "layer": layer,
        "layer_order": order,
        "node_count": 0,
        "public_node_count": 0,
        "internal_node_count": 0,
        "candidate_node_count": 0,
        "source_count": 0,
        "edge_count": 0,
        "public_edge_count": 0,
        "lead_or_disputed_edge_count": 0,
        "public_ready_edge_count": 0,
        "_statuses": {},
        "_classes": {},
    })
