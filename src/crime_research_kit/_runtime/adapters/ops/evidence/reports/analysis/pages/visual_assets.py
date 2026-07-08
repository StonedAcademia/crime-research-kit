"""External asset writers for generated visual packages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.render import _static_assets

NETWORK_KINDS = {"cytoscape-network", "cytoscape-clustered-network"}


def write_visual_assets(out: Path, package: dict[str, Any]) -> list[str]:
    artifacts = _write_static(out)
    for console in package["consoles"].values():
        artifacts.extend(_write_console_data(out, console))
    return artifacts


def _write_static(out: Path) -> list[str]:
    css, js = _static_assets()
    static = out / "static"
    static.mkdir(parents=True, exist_ok=True)
    static.joinpath("app.css").write_text(css + "\n", encoding="utf-8")
    static.joinpath("app.js").write_text(js + "\n", encoding="utf-8")
    return ["static/app.css", "static/app.js"]


def _write_console_data(out: Path, console: dict[str, Any]) -> list[str]:
    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    slug = str(console["slug"])
    if console.get("kind") not in NETWORK_KINDS:
        _write_js(data_dir / f"{slug}.js", slug, console)
        return [f"data/{slug}.js"]
    variants = {
        "default": _network_payload(console, {"default"}),
        "context": _network_payload(console, {"default", "context"}),
        "all": _network_payload(console, {"default", "context", "hidden_by_default", "internal"}),
    }
    artifacts = []
    for variant, payload in variants.items():
        key = slug if variant == "default" else f"{slug}:{variant}"
        filename = f"{slug}.js" if variant == "default" else f"{slug}.{variant}.js"
        _write_js(data_dir / filename, key, payload)
        artifacts.append(f"data/{filename}")
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


def _nodes_for_edges(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], *, include_all: bool) -> list[dict[str, Any]]:
    if include_all:
        return nodes
    if not edges:
        return nodes[:80]
    node_ids = {str(edge.get("src_id")) for edge in edges} | {str(edge.get("dst_id")) for edge in edges}
    return [node for node in nodes if str(node.get("node_id")) in node_ids]


def _write_js(path: Path, key: str, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    path.write_text(
        "window.__CRK_VISUAL_DATA__=window.__CRK_VISUAL_DATA__||{};\n"
        f"window.__CRK_VISUAL_DATA__[{json.dumps(key)}]={data};\n",
        encoding="utf-8",
    )
