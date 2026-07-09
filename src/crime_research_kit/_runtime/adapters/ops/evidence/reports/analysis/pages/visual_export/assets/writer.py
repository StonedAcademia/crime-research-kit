"""External asset writers for generated visual packages."""

from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import shutil
from typing import Any

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.render import _static_assets
from crime_research_kit._runtime.adapters.ops.evidence.reports.common import parse_cell_list

NETWORK_KINDS = {"cytoscape-network", "cytoscape-clustered-network"}


def write_visual_assets(out: Path, package: dict[str, Any]) -> list[str]:
    artifacts = _write_static(out)
    for console in package["consoles"].values():
        artifacts.extend(_write_console_data(out, console))
    private_package = package.get("private_package")
    if private_package:
        for console in private_package["consoles"].values():
            artifacts.extend(_write_console_data(out, console, data_prefix="data/private", key_prefix="private:"))
    else:
        shutil.rmtree(out / "data" / "private", ignore_errors=True)
    return artifacts


def _write_static(out: Path) -> list[str]:
    css, js = _static_assets()
    static = out / "static"
    static.mkdir(parents=True, exist_ok=True)
    static.joinpath("app.css").write_text(css + "\n", encoding="utf-8")
    static.joinpath("app.js").write_text(js + "\n", encoding="utf-8")
    return ["static/app.css", "static/app.js"]


def _write_console_data(out: Path, console: dict[str, Any], *, data_prefix: str = "data", key_prefix: str = "") -> list[str]:
    data_dir = out / data_prefix
    data_dir.mkdir(parents=True, exist_ok=True)
    slug = str(console["slug"])
    if console.get("kind") not in NETWORK_KINDS:
        _write_js(data_dir / f"{slug}.js", f"{key_prefix}{slug}", console)
        return [f"{data_prefix}/{slug}.js"]
    default = (
        _cluster_overview_payload(console)
        if slug == "relationship_network"
        else _network_payload(console, {"default"})
    )
    variants = {
        "default": default,
        "context": _network_payload(console, {"default", "context"}),
        "all": _network_payload(console, {"default", "context", "hidden_by_default", "internal"}),
    }
    artifacts = []
    for variant, payload in variants.items():
        key = f"{key_prefix}{slug}" if variant == "default" else f"{key_prefix}{slug}:{variant}"
        filename = f"{slug}.js" if variant == "default" else f"{slug}.{variant}.js"
        _write_js(data_dir / filename, key, payload)
        artifacts.append(f"{data_prefix}/{filename}")
    return artifacts


def _network_payload(console: dict[str, Any], visible: set[str]) -> dict[str, Any]:
    data = console.get("data", {})
    edges = [edge for edge in data.get("edges", []) if str(edge.get("edge_visibility", "default")) in visible]
    nodes = _nodes_for_edges(data.get("nodes", []), edges, include_all="hidden_by_default" in visible and console.get("include_private"))
    return {
        "slug": console.get("slug"),
        "title": console.get("title"),
        "kind": console.get("kind"),
        "include_private": console.get("include_private"),
        "graph_variants": ["default", "context", "all"],
        "data": {"nodes": nodes, "edges": edges},
        "audit_files": console.get("audit_files", []),
    }


def _cluster_overview_payload(console: dict[str, Any]) -> dict[str, Any]:
    data = console.get("data", {})
    nodes = _cluster_nodes(data.get("clusters", []))
    labels = {str(node["cluster_id"]): str(node["cluster_label"]) for node in nodes}
    return {
        "slug": console.get("slug"),
        "title": console.get("title"),
        "kind": console.get("kind"),
        "include_private": console.get("include_private"),
        "graph_variants": ["default", "context", "all"],
        "layout": "preset",
        "show_all_nodes": True,
        "overview_mode": "cluster_aggregate",
        "data": {"nodes": nodes, "edges": _cluster_edges(data.get("edges", []), labels)},
        "audit_files": console.get("audit_files", []),
    }


def _cluster_nodes(clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(clusters, key=lambda row: _cluster_sort_key(str(row.get("cluster_id", ""))))
    numbered = [row for row in ordered if _range_start(str(row.get("cluster_id", ""))) is not None]
    context = [row for row in ordered if _range_start(str(row.get("cluster_id", ""))) is None]
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(numbered):
        rows.append(_cluster_node(row, *_grid_xy(idx, 4, 130)))
    context_start = 130 + math.ceil(len(numbered) / 4) * 135 + 70
    for idx, row in enumerate(context):
        rows.append(_cluster_node(row, *_grid_xy(idx, 4, context_start)))
    return rows


def _cluster_node(row: dict[str, Any], x: float, y: float) -> dict[str, Any]:
    cid = str(row.get("cluster_id", ""))
    label = str(row.get("cluster_label") or cid)
    node = dict(row)
    node.update({
        "node_id": f"CLUSTER:{cid}",
        "label": label,
        "cluster_id": cid,
        "cluster_label": label,
        "facet_types": row.get("top_facets", ""),
        "hub_role": "",
        "degree": row.get("edge_count", 0),
        "x": round(x, 2),
        "y": round(y, 2),
    })
    return node


def _cluster_edges(edges: list[dict[str, Any]], labels: dict[str, str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for edge in edges:
        if str(edge.get("edge_visibility", "default")) != "default":
            continue
        left = str(edge.get("src_cluster_id", ""))
        right = str(edge.get("dst_cluster_id", ""))
        if left == right or left not in labels or right not in labels:
            continue
        key = tuple(sorted((left, right), key=_cluster_sort_key))
        item = grouped.setdefault(
            key,
            {"facets": Counter(), "source_ids": set(), "claim_ids": set(), "count": 0},
        )
        item["count"] += 1
        item["facets"].update(parse_cell_list(edge.get("facet_types")))
        item["source_ids"].update(parse_cell_list(edge.get("source_ids")))
        item["claim_ids"].update(parse_cell_list(edge.get("claim_ids")))
    rows = []
    for (left, right), item in sorted(
        grouped.items(),
        key=lambda pair: (-int(pair[1]["count"]), pair[0]),
    ):
        facets = [name for name, _ in item["facets"].most_common(6)]
        count = int(item["count"])
        rows.append({
            "edge_id": f"CLUSTER_EDGE:{left}:{right}",
            "src_id": f"CLUSTER:{left}",
            "dst_id": f"CLUSTER:{right}",
            "src_label": labels[left],
            "dst_label": labels[right],
            "relationship_class": "cluster_aggregate",
            "edge_visibility": "default",
            "edge_weight": round(min(3.2, 0.65 + math.log1p(count) * 0.55), 3),
            "facet_types": ";".join(facets or ["context"]),
            "relationship_count": count,
            "source_count": len(item["source_ids"]),
            "claim_count": len(item["claim_ids"]),
            "source_ids": sorted(item["source_ids"]),
            "claim_ids": sorted(item["claim_ids"]),
        })
    return rows


def _nodes_for_edges(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], *, include_all: bool) -> list[dict[str, Any]]:
    if include_all:
        return nodes
    if not edges:
        return nodes[:80]
    node_ids = {str(edge.get("src_id")) for edge in edges} | {str(edge.get("dst_id")) for edge in edges}
    return [node for node in nodes if str(node.get("node_id")) in node_ids]


def _grid_xy(index: int, columns: int, y_start: int) -> tuple[float, float]:
    col = index % columns
    row = index // columns
    return 140 + col * 245, y_start + row * 135


def _cluster_sort_key(value: str) -> tuple[int, int, str]:
    start = _range_start(value)
    if start is not None:
        return (0, start, value)
    order = {
        "PROGRAM_CONTEXT": 0,
        "DOCUMENT_CONTEXT": 1,
        "EVENT_CONTEXT": 2,
        "ENTITY_CONTEXT": 3,
        "INTERCLUSTER": 4,
    }
    return (1, order.get(value, 99), value)


def _range_start(value: str) -> int | None:
    parts = value.split("_")
    if len(parts) == 3 and parts[0] == "SP" and parts[1].isdigit():
        return int(parts[1])
    return None


def _write_js(path: Path, key: str, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    path.write_text(
        "window.__CRK_VISUAL_DATA__=window.__CRK_VISUAL_DATA__||{};\n"
        f"window.__CRK_VISUAL_DATA__[{json.dumps(key)}]={data};\n",
        encoding="utf-8",
    )
