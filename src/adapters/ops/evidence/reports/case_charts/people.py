"""People graph report page and SVG figure builders."""

from __future__ import annotations

import math
from typing import Any

from core.models.reports import Circle, Group, Line, MetricBlock, ReportPage, SvgDoc, SvgElement, TableBlock, Text

from adapters.ops.evidence.ledger.records import flatten
from adapters.ops.evidence.reports.analysis.pages.render import render_page, render_svg_doc
from adapters.ops.evidence.reports.common import (
    edge_evidence_label,
    edge_is_lead_only,
    entity_display,
    people_graph_groups,
    truncate_label,
)
from adapters.ops.evidence.reports.weights import evidence_edge_weight, parse_float


def render_people_graph_html(
    case_title: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    include_private: bool,
) -> str:
    return render_page(build_people_graph_page(case_title, nodes, edges, include_private))


def build_people_graph_page(
    case_title: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    include_private: bool,
) -> ReportPage:
    weighted_edges, group_by_id, groups, degree, weighted_degree = _graph_state(nodes, edges)
    metrics = [
        MetricBlock(label="People", value=str(len(nodes))),
        MetricBlock(label="Edges", value=str(len(weighted_edges))),
        MetricBlock(label="Connected groups", value=str(len(groups))),
        MetricBlock(label="Strong / lead edges", value=f"{sum(1 for edge in weighted_edges if parse_float(edge.get('edge_weight'), 0.0) >= 0.7)}/{sum(1 for edge in weighted_edges if edge_is_lead_only(edge))}"),
    ]
    return ReportPage(
        slug="people_graph",
        title="Evidence-weighted people graph",
        case_title=case_title,
        summary=f"Scope: {_scope(include_private)}. Edges are source-bound direct person-person relationships or shared event/context links; contextual links do not imply direct participation.",
        include_private=include_private,
        back_href="charts.md",
        back_label="Back to case charts index",
        figure=_people_graph_figure_from(nodes, weighted_edges, group_by_id, groups, degree, weighted_degree),
        metrics=metrics,
        notes=["Legend: higher-weight evidence edge; medium evidence edge; lead/context edge. Node outline color marks graph group; node size follows weighted degree."],
        tables=[
            TableBlock(title="Graph Groups", columns=["group", "people", "members"], rows=_group_rows(groups), limit=max(1, len(groups))),
            TableBlock(title="People", columns=["group", "person", "status", "degree", "weighted_degree", "roles", "sources"], rows=_node_rows(nodes, group_by_id, degree, weighted_degree), limit=max(1, len(nodes))),
            TableBlock(title="Edges", columns=["person", "person_2", "evidence", "weight", "status", "confidence", "connection", "events", "claims", "sources"], rows=_edge_rows(weighted_edges), limit=max(1, len(weighted_edges))),
        ],
    )


def build_people_graph_figure(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> SvgDoc:
    weighted_edges, group_by_id, groups, degree, weighted_degree = _graph_state(nodes, edges)
    return _people_graph_figure_from(nodes, weighted_edges, group_by_id, groups, degree, weighted_degree)


def render_people_graph_svg(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    return render_svg_doc(build_people_graph_figure(nodes, edges))


def _scope(include_private: bool) -> str:
    return "public and internal rows" if include_private else "public-export rows only"


def _graph_state(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str], list[list[dict[str, Any]]], dict[str, int], dict[str, float]]:
    weighted_edges = [dict(edge, edge_weight=evidence_edge_weight(edge)) for edge in edges]
    group_by_id, groups = people_graph_groups(nodes, weighted_edges)
    degree = {str(node.get("entity_id", "")): 0 for node in nodes}
    weighted_degree = {str(node.get("entity_id", "")): 0.0 for node in nodes}
    for edge in weighted_edges:
        weight = parse_float(edge.get("edge_weight"), 0.0)
        for node_id in [str(edge.get("src_entity_id", "")), str(edge.get("dst_entity_id", ""))]:
            if node_id in degree:
                degree[node_id] += 1
                weighted_degree[node_id] += weight
    return weighted_edges, group_by_id, groups, degree, weighted_degree


def _people_graph_figure_from(nodes: list[dict[str, Any]], weighted_edges: list[dict[str, Any]], group_by_id: dict[str, str], groups: list[list[dict[str, Any]]], degree: dict[str, int], weighted_degree: dict[str, float]) -> SvgDoc:
    width = 1320
    height = max(820, 650 + (len(nodes) * 7))
    positions = _positions(width, height, groups)
    elements = [*_edge_lines(weighted_edges, positions), *_node_shapes(nodes, positions, group_by_id, degree, weighted_degree)]
    return SvgDoc(width=width, height=height, view_box=f"0 0 {width} {height}", role="img", aria_label="People-only connection graph", elements=elements)


def _positions(width: int, height: int, groups: list[list[dict[str, Any]]]) -> dict[str, tuple[float, float]]:
    positions: dict[str, tuple[float, float]] = {}
    cx = width / 2
    cy = height / 2
    for group_idx, group in enumerate(groups):
        angle = (2 * math.pi * group_idx / max(1, len(groups))) - (math.pi / 2)
        group_x = cx if len(groups) == 1 else cx + 440 * math.cos(angle)
        group_y = cy if len(groups) == 1 else cy + 255 * math.sin(angle)
        member_radius = 0 if len(group) == 1 else min(96, 46 + (len(group) * 10))
        for member_idx, node in enumerate(group):
            member_angle = (2 * math.pi * member_idx / len(group)) - (math.pi / 2) if len(group) > 1 else 0
            x = group_x if len(group) == 1 else group_x + member_radius * math.cos(member_angle)
            y = group_y if len(group) == 1 else group_y + member_radius * math.sin(member_angle)
            positions[str(node["entity_id"])] = (x, y)
    return positions


def _edge_lines(weighted_edges: list[dict[str, Any]], positions: dict[str, tuple[float, float]]) -> list[SvgElement]:
    lines: list[SvgElement] = []
    for edge in weighted_edges:
        src = str(edge["src_entity_id"])
        dst = str(edge["dst_entity_id"])
        if src not in positions or dst not in positions:
            continue
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        weight = parse_float(edge.get("edge_weight"), 0.0)
        stroke = "#1d4ed8" if weight >= 0.7 else "#64748b" if weight >= 0.35 else "#94a3b8"
        title = f"{edge.get('src_name', src)} - {edge.get('dst_name', dst)} | {flatten(edge.get('connection_types'))} | status={flatten(edge.get('statuses')) or 'unknown'} | weight={weight:.2f}"
        lines.append(Line(x1=x1, y1=y1, x2=x2, y2=y2, css_class="edge", stroke=stroke, stroke_width=1.2 + (weight * 4), stroke_dasharray="7 7" if edge_is_lead_only(edge) else "", title=title))
    return lines


def _node_shapes(nodes: list[dict[str, Any]], positions: dict[str, tuple[float, float]], group_by_id: dict[str, str], degree: dict[str, int], weighted_degree: dict[str, float]) -> list[SvgElement]:
    colors = ["#2563eb", "#0f766e", "#7c3aed", "#b45309", "#be123c", "#475569", "#15803d", "#0369a1"]
    shapes: list[SvgElement] = []
    for node in nodes:
        entity_id = str(node["entity_id"])
        x, y = positions[entity_id]
        group_id = group_by_id.get(entity_id, "G?")
        group_num = int(group_id[1:]) if group_id[1:].isdigit() else 1
        node_radius = 29 + min(12, weighted_degree.get(entity_id, 0.0) * 5)
        fill = "#fff7ed" if node.get("public_export", True) is False else "#ffffff"
        title = f"{entity_display(node)} | group={group_id} | roles={flatten(node.get('role_tags'))} | claims={flatten(node.get('claim_ids'))} | sources={flatten(node.get('source_ids'))}"
        shapes.append(Group(title=title, children=[
            Circle(cx=x, cy=y, r=node_radius, css_class="node", stroke=colors[(group_num - 1) % len(colors)], fill=fill, stroke_width=4),
            Text(x=x, y=y + node_radius + 18, content=truncate_label(entity_display(node), 24), css_class="node-label", anchor="middle"),
            Text(x=x, y=y + node_radius + 34, content=truncate_label(f"{group_id} | {node.get('status', 'unknown')} | deg {degree.get(entity_id, 0)}", 34), css_class="node-sub", anchor="middle"),
        ]))
    return shapes


def _group_rows(groups: list[list[dict[str, Any]]]) -> list[dict[str, str]]:
    return [{"group": f"G{idx}", "people": str(len(group)), "members": "; ".join(entity_display(node) for node in group)} for idx, group in enumerate(groups, start=1)]


def _node_rows(nodes: list[dict[str, Any]], group_by_id: dict[str, str], degree: dict[str, int], weighted_degree: dict[str, float]) -> list[dict[str, str]]:
    return [{"group": group_by_id.get(str(node.get("entity_id")), ""), "person": entity_display(node), "status": str(node.get("status", "")), "degree": str(degree.get(str(node.get("entity_id")), 0)), "weighted_degree": f"{weighted_degree.get(str(node.get('entity_id')), 0.0):.2f}", "roles": flatten(node.get("role_tags")), "sources": flatten(node.get("source_ids"))} for node in sorted(nodes, key=lambda row: (group_by_id.get(str(row.get("entity_id")), ""), entity_display(row)))]


def _edge_rows(weighted_edges: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [{"person": str(edge["src_name"]), "person_2": str(edge["dst_name"]), "evidence": edge_evidence_label(edge), "weight": f"{edge.get('edge_weight', 0):.2f}", "status": flatten(edge.get("statuses")), "confidence": str(edge.get("confidence", "")), "connection": flatten(edge.get("connection_types")), "events": flatten(edge.get("event_ids")), "claims": flatten(edge.get("claim_ids")), "sources": flatten(edge.get("source_ids"))} for edge in sorted(weighted_edges, key=lambda row: (-parse_float(row.get("edge_weight"), 0.0), row["src_name"], row["dst_name"]))]
