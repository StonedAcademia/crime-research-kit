"""People cluster report page and SVG figure builders."""

from __future__ import annotations

import math
from typing import Any

from core.models.reports import Circle, Line, ReportPage, SvgDoc, SvgElement, TableBlock, Text

from adapters.ops.evidence.reports.analysis.pages.render import render_page, render_svg_doc
from adapters.ops.evidence.reports.common import entity_display, parse_cell_list, truncate_label
from adapters.ops.evidence.reports.weights import parse_float


def render_people_clusters_html(
    case_title: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    cluster_by_id: dict[str, str],
    density_by_id: dict[str, float],
    include_private: bool,
) -> str:
    return render_page(build_people_clusters_page(case_title, nodes, edges, cluster_by_id, density_by_id, include_private))


def build_people_clusters_page(
    case_title: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    cluster_by_id: dict[str, str],
    density_by_id: dict[str, float],
    include_private: bool,
) -> ReportPage:
    return ReportPage(
        slug="people_clusters",
        title="Leiden people clusters",
        case_title=case_title,
        summary=f"Scope: {'public and internal rows' if include_private else 'public-export rows only'}. Edge weights are evidence-weighted; node size is graph-kernel density. Dashed edges include weak co-mentions and should be treated as leads only.",
        include_private=include_private,
        back_href="clusters.md",
        back_label="Back to clusters index",
        figure=build_people_clusters_figure(nodes, edges, cluster_by_id, density_by_id),
        tables=[
            TableBlock(title="Clustered People", columns=["cluster", "person", "kde", "status", "public_export"], rows=_node_rows(nodes, cluster_by_id, density_by_id), limit=max(1, len(nodes))),
            TableBlock(title="Weighted Edges", columns=["person", "person_2", "weight", "connection", "status"], rows=_edge_rows(edges), limit=max(1, len(edges))),
        ],
    )


def build_people_clusters_figure(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    cluster_by_id: dict[str, str],
    density_by_id: dict[str, float],
) -> SvgDoc:
    width = 1280
    height = 820
    positions = _positions(width, height, nodes, cluster_by_id)
    elements = [*_edge_lines(edges, positions), *_node_shapes(nodes, positions, cluster_by_id, density_by_id)]
    return SvgDoc(width=width, height=height, view_box=f"0 0 {width} {height}", role="img", aria_label="Leiden people clusters", elements=elements)


def render_people_clusters_svg(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], cluster_by_id: dict[str, str], density_by_id: dict[str, float]) -> str:
    return render_svg_doc(build_people_clusters_figure(nodes, edges, cluster_by_id, density_by_id))


def _positions(width: int, height: int, nodes: list[dict[str, Any]], cluster_by_id: dict[str, str]) -> dict[str, tuple[float, float]]:
    clusters: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        clusters.setdefault(cluster_by_id[str(node["entity_id"])], []).append(node)
    positions: dict[str, tuple[float, float]] = {}
    cx = width / 2
    cy = height / 2
    for cluster_idx, cluster_id in enumerate(sorted(clusters)):
        angle = (2 * math.pi * cluster_idx / max(1, len(clusters))) - (math.pi / 2)
        cluster_x = cx + 250 * math.cos(angle)
        cluster_y = cy + 250 * math.sin(angle)
        members = sorted(clusters[cluster_id], key=entity_display)
        member_radius = 48 if len(members) > 1 else 0
        for member_idx, node in enumerate(members):
            member_angle = (2 * math.pi * member_idx / len(members)) - (math.pi / 2) if len(members) > 1 else 0
            x = cluster_x if len(members) == 1 else cluster_x + member_radius * math.cos(member_angle)
            y = cluster_y if len(members) == 1 else cluster_y + member_radius * math.sin(member_angle)
            positions[str(node["entity_id"])] = (x, y)
    return positions


def _edge_lines(edges: list[dict[str, Any]], positions: dict[str, tuple[float, float]]) -> list[SvgElement]:
    lines: list[SvgElement] = []
    for edge in edges:
        src = str(edge["src_entity_id"])
        dst = str(edge["dst_entity_id"])
        if src not in positions or dst not in positions:
            continue
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        weight = parse_float(edge.get("edge_weight"), 0.0)
        dashed = "6 6" if "co_mentioned_with" in parse_cell_list(edge.get("connection_types")) else ""
        lines.append(Line(x1=x1, y1=y1, x2=x2, y2=y2, css_class="edge", stroke_width=0.75 + (weight * 4), stroke_dasharray=dashed))
    return lines


def _node_shapes(nodes: list[dict[str, Any]], positions: dict[str, tuple[float, float]], cluster_by_id: dict[str, str], density_by_id: dict[str, float]) -> list[SvgElement]:
    colors = ["#2563eb", "#0f766e", "#7c3aed", "#b45309", "#be123c", "#475569", "#15803d", "#0369a1"]
    shapes: list[SvgElement] = []
    for node in nodes:
        entity_id = str(node["entity_id"])
        x, y = positions[entity_id]
        cluster_id = cluster_by_id[entity_id]
        color = colors[(int(cluster_id[1:]) - 1) % len(colors)] if cluster_id[1:].isdigit() else colors[0]
        density = density_by_id.get(entity_id, 0.0)
        radius = 24 + min(16, density * 18)
        shapes.extend([
            Circle(cx=x, cy=y, r=radius, css_class="node", stroke=color, stroke_width=4),
            Text(x=x, y=y + radius + 18, content=truncate_label(entity_display(node), 24), css_class="node-label", anchor="middle"),
            Text(x=x, y=y + radius + 34, content=f"{cluster_id} kde={density:.2f}", css_class="node-sub", anchor="middle"),
        ])
    return shapes


def _node_rows(nodes: list[dict[str, Any]], cluster_by_id: dict[str, str], density_by_id: dict[str, float]) -> list[dict[str, str]]:
    return [{"cluster": cluster_by_id[str(node["entity_id"])], "person": entity_display(node), "kde": f"{density_by_id.get(str(node['entity_id']), 0.0):.6f}", "status": str(node.get("status", "")), "public_export": str(node.get("public_export", ""))} for node in sorted(nodes, key=lambda row: (cluster_by_id[str(row["entity_id"])], entity_display(row)))]


def _edge_rows(edges: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [{"person": str(edge.get("src_name", "")), "person_2": str(edge.get("dst_name", "")), "weight": str(edge.get("edge_weight", "")), "connection": str(edge.get("connection_types", "")), "status": str(edge.get("statuses", ""))} for edge in sorted(edges, key=lambda row: (str(row.get("src_name", "")), str(row.get("dst_name", ""))))]
