"""Layered network SVG figure builders for analysis chart exports."""

from __future__ import annotations

import math
from typing import Any

from crime_research_kit._runtime.core.models.reports import Circle, Group, Line, Path, Rect, SvgDoc, SvgElement, Text

from crime_research_kit._runtime.adapters.ops.evidence.ledger.records import flatten
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.svg.base import color_for, short_label
from crime_research_kit._runtime.adapters.ops.evidence.reports.weights import parse_float


def _chart_doc(width: int, height: int, label: str, elements: list[SvgElement], style: str = "") -> SvgDoc:
    return SvgDoc(
        width=width, height=height, view_box=f"0 0 {width} {height}", css_class="chart-svg", style=style, role="img", aria_label=label,
        elements=[Rect(x=0, y=0, width=width, height=height, rx=8, css_class="chart-bg"), *elements],
    )


def _no_data_figure() -> SvgDoc:
    return _chart_doc(900, 220, "No chart data", [Text(x=450, y=112, content="No chart data", css_class="axis-label", anchor="middle")])


def build_layered_graph_figure(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> SvgDoc:
    if not nodes:
        return _no_data_figure()
    degree: dict[str, int] = {}
    for edge in edges:
        degree[str(edge.get("src_id", ""))] = degree.get(str(edge.get("src_id", "")), 0) + 1
        degree[str(edge.get("dst_id", ""))] = degree.get(str(edge.get("dst_id", "")), 0) + 1
    selected = sorted(nodes, key=lambda row: (-degree.get(str(row.get("node_id")), 0), str(row.get("label", ""))))[:64]
    selected_ids = {str(row.get("node_id")) for row in selected}
    layers = sorted({str(row.get("layer") or "entity") for row in selected})
    width, height = 1120, 620
    positions: dict[str, tuple[float, float]] = {}
    for layer_idx, layer in enumerate(layers):
        layer_nodes = [row for row in selected if str(row.get("layer") or "entity") == layer]
        x = 80 + layer_idx * ((width - 160) / max(1, len(layers) - 1))
        step = (height - 140) / max(1, len(layer_nodes))
        for idx, row in enumerate(layer_nodes):
            y = 88 + idx * step + step / 2
            positions[str(row.get("node_id"))] = (x, y)
    edge_lines: list[SvgElement] = []
    for edge in edges:
        src = str(edge.get("src_id", ""))
        dst = str(edge.get("dst_id", ""))
        if src not in selected_ids or dst not in selected_ids or src not in positions or dst not in positions:
            continue
        sx, sy = positions[src]
        dx, dy = positions[dst]
        edge_lines.append(
            Line(
                x1=f"{sx:.1f}", y1=f"{sy:.1f}", x2=f"{dx:.1f}", y2=f"{dy:.1f}",
                stroke=color_for(edge.get("status")),
                stroke_width=f"{max(1.0, parse_float(edge.get('source_count'), 1.0)):.1f}",
                stroke_opacity="0.22",
                title=flatten(edge.get("relation_type")),
            )
        )
    node_marks: list[SvgElement] = []
    for row in selected:
        node_id = str(row.get("node_id"))
        x, y = positions[node_id]
        radius = 5 + min(11, degree.get(node_id, 0))
        node_marks.append(
            Group(children=[
                Circle(cx=f"{x:.1f}", cy=f"{y:.1f}", r=radius, fill=color_for(row.get("status"), len(node_marks)), stroke="#fff", stroke_width=1.5),
                Text(x=f"{x + 14:.1f}", y=f"{y + 4:.1f}", content=short_label(row.get("label"), 24), css_class="mini-label"),
            ])
        )
    layer_labels = [
        Text(x=f"{80 + idx * ((width - 160) / max(1, len(layers) - 1)):.1f}", y=46, content=layer, css_class="axis-label", anchor="middle")
        for idx, layer in enumerate(layers)
    ]
    return _chart_doc(width, height, "Layered knowledge graph", [*layer_labels, *edge_lines, *node_marks])


def build_layered_graph_v2_figure(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> SvgDoc:
    if not nodes:
        return _no_data_figure()
    degree = {str(row.get("node_id", "")): int(parse_float(row.get("degree"), 0.0)) for row in nodes}
    selected = sorted(
        nodes,
        key=lambda row: (
            int(parse_float(row.get("layer_order"), 99)),
            -degree.get(str(row.get("node_id", "")), 0),
            -parse_float(row.get("source_count"), 0.0),
            str(row.get("label", "")),
        ),
    )[:120]
    selected_ids = {str(row.get("node_id")) for row in selected}
    layers = sorted(
        {str(row.get("layer") or "entity") for row in selected},
        key=lambda layer: min(int(parse_float(row.get("layer_order"), 99)) for row in selected if str(row.get("layer") or "entity") == layer),
    )
    width, height = 1440, 860
    left, right, top, bottom = 74, 72, 92, 82
    lane_width = width - left - right
    lane_height = height - top - bottom
    positions: dict[str, tuple[float, float]] = {}
    for layer_idx, layer in enumerate(layers):
        layer_nodes = [row for row in selected if str(row.get("layer") or "entity") == layer]
        x = left + layer_idx * (lane_width / max(1, len(layers) - 1))
        step = lane_height / max(1, len(layer_nodes))
        for idx, row in enumerate(layer_nodes):
            y = top + idx * step + step / 2
            positions[str(row.get("node_id"))] = (x, y)
    layer_guides: list[SvgElement] = []
    for idx, layer in enumerate(layers):
        x = left + idx * (lane_width / max(1, len(layers) - 1))
        layer_guides.extend([
            Line(x1=f"{x:.1f}", y1=top - 26, x2=f"{x:.1f}", y2=height - bottom + 22, stroke="#e3ebf2"),
            Text(x=f"{x:.1f}", y=50, content=layer, css_class="axis-label", anchor="middle"),
        ])
    edge_marks: list[SvgElement] = []
    for edge in sorted(edges, key=lambda row: parse_float(row.get("evidence_weight"), 0.0)):
        src = str(edge.get("src_id", ""))
        dst = str(edge.get("dst_id", ""))
        if src not in selected_ids or dst not in selected_ids or src not in positions or dst not in positions:
            continue
        sx, sy = positions[src]
        dx, dy = positions[dst]
        mid = abs(dx - sx) * 0.42
        c1 = sx + mid
        c2 = dx - mid
        weight = max(1.0, min(5.5, 1.0 + parse_float(edge.get("evidence_weight"), 0.0) * 3.4))
        readiness = str(edge.get("readiness", ""))
        title = (
            f"{edge.get('src_label')} -> {edge.get('dst_label')} | {edge.get('relation_type')} | "
            f"{edge.get('relationship_class')} | {edge.get('status')} | readiness={readiness} | "
            f"sources={edge.get('source_count')} | caveat={edge.get('caveat')}"
        )
        edge_marks.append(
            Path(
                d=f"M {sx:.1f} {sy:.1f} C {c1:.1f} {sy:.1f}, {c2:.1f} {dy:.1f}, {dx:.1f} {dy:.1f}",
                fill="none",
                stroke=color_for(readiness or edge.get("status")),
                stroke_width=f"{weight:.2f}",
                stroke_opacity="0.22",
                stroke_dasharray="7 7" if str(edge.get("caveat", "")) else "",
                title=flatten(title),
            )
        )
    node_marks: list[SvgElement] = []
    for row in selected:
        node_id = str(row.get("node_id"))
        x, y = positions[node_id]
        radius = 5.5 + min(13.0, math.sqrt(max(0, degree.get(node_id, 0))) * 3.1)
        readiness = str(row.get("readiness") or row.get("evidence_state") or row.get("status"))
        title = (
            f"{row.get('label')} | layer={row.get('layer')} | cluster={row.get('cluster_id')} | "
            f"status={row.get('status')} | readiness={row.get('readiness')} | evidence={row.get('evidence_state')} | "
            f"sources={row.get('source_count')} | degree={row.get('degree')} | caveat={row.get('caveat')}"
        )
        node_marks.append(
            Group(children=[
                Circle(
                    cx=f"{x:.1f}", cy=f"{y:.1f}", r=f"{radius:.1f}", fill=color_for(readiness),
                    fill_opacity="0.9", stroke="#fff", stroke_width=1.6, title=flatten(title),
                ),
                Text(x=f"{x + radius + 7:.1f}", y=f"{y + 4:.1f}", content=short_label(row.get("label"), 22), css_class="mini-label"),
            ])
        )
    legend = [
        ("public_ready", "public ready"),
        ("usable_with_context", "context"),
        ("source_note_required", "single source"),
        ("lead_or_disputed", "lead/disputed"),
        ("internal_only", "internal"),
    ]
    legend_marks: list[SvgElement] = []
    for idx, (key, label) in enumerate(legend):
        x = left + idx * 150
        y = height - 34
        legend_marks.append(
            Group(children=[
                Circle(cx=x, cy=y, r=7, fill=color_for(key)),
                Text(x=x + 14, y=y + 4, content=label, css_class="mini-label"),
            ])
        )
    headline = Text(
        x=left,
        y=24,
        content="Layered evidence navigation graph: node color reflects readiness/evidence state; dashed edges require caveats.",
        css_class="axis-label",
    )
    return _chart_doc(width, height, "Layered knowledge graph v2", [headline, *layer_guides, *edge_marks, *node_marks, *legend_marks], style=f"min-width:{width}px")
