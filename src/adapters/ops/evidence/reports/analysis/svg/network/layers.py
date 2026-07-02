"""Layered network SVG renderers for analysis chart exports."""

from __future__ import annotations

import html
import math
from typing import Any

from adapters.ops.evidence.reports.analysis.svg.base import color_for, html_title, short_label, svg_no_data
from adapters.ops.evidence.reports.weights import parse_float


def render_layered_graph_svg(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    if not nodes:
        return svg_no_data()
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
    edge_lines = []
    for edge in edges:
        src = str(edge.get("src_id", ""))
        dst = str(edge.get("dst_id", ""))
        if src not in selected_ids or dst not in selected_ids or src not in positions or dst not in positions:
            continue
        sx, sy = positions[src]
        dx, dy = positions[dst]
        edge_lines.append(
            f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{dx:.1f}" y2="{dy:.1f}" '
            f'stroke="{color_for(edge.get("status"))}" stroke-width="{max(1.0, parse_float(edge.get("source_count"), 1.0)):.1f}" stroke-opacity="0.22">'
            f'{html_title(edge.get("relation_type"))}</line>'
        )
    node_marks = []
    for row in selected:
        node_id = str(row.get("node_id"))
        x, y = positions[node_id]
        radius = 5 + min(11, degree.get(node_id, 0))
        node_marks.append(
            f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{color_for(row.get("status"), len(node_marks))}" stroke="#fff" stroke-width="1.5"/>'
            f'<text x="{x + 14:.1f}" y="{y + 4:.1f}" class="mini-label">{html.escape(short_label(row.get("label"), 24))}</text></g>'
        )
    layer_labels = "".join(
        f'<text x="{80 + idx * ((width - 160) / max(1, len(layers) - 1)):.1f}" y="46" class="axis-label" text-anchor="middle">{html.escape(layer)}</text>'
        for idx, layer in enumerate(layers)
    )
    return (
        '<div class="chart-shell">'
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Layered knowledge graph">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        f'{layer_labels}{"".join(edge_lines)}{"".join(node_marks)}'
        "</svg></div>"
    )


def render_layered_graph_v2_svg(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    if not nodes:
        return svg_no_data()
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
    layer_guides = []
    for idx, layer in enumerate(layers):
        x = left + idx * (lane_width / max(1, len(layers) - 1))
        layer_guides.append(
            f'<line x1="{x:.1f}" y1="{top - 26}" x2="{x:.1f}" y2="{height - bottom + 22}" stroke="#e3ebf2" stroke-width="1"/>'
            f'<text x="{x:.1f}" y="50" class="axis-label" text-anchor="middle">{html.escape(layer)}</text>'
        )
    edge_marks = []
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
        dash = ' stroke-dasharray="7 7"' if str(edge.get("caveat", "")) else ""
        title = (
            f"{edge.get('src_label')} -> {edge.get('dst_label')} | {edge.get('relation_type')} | "
            f"{edge.get('relationship_class')} | {edge.get('status')} | readiness={readiness} | "
            f"sources={edge.get('source_count')} | caveat={edge.get('caveat')}"
        )
        edge_marks.append(
            f'<path d="M {sx:.1f} {sy:.1f} C {c1:.1f} {sy:.1f}, {c2:.1f} {dy:.1f}, {dx:.1f} {dy:.1f}" '
            f'fill="none" stroke="{color_for(readiness or edge.get("status"))}" stroke-width="{weight:.2f}" '
            f'stroke-opacity="0.22"{dash}>{html_title(title)}</path>'
        )
    node_marks = []
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
        label = html.escape(short_label(row.get("label"), 22))
        node_marks.append(
            f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color_for(readiness)}" '
            f'fill-opacity="0.9" stroke="#fff" stroke-width="1.6">{html_title(title)}</circle>'
            f'<text x="{x + radius + 7:.1f}" y="{y + 4:.1f}" class="mini-label">{label}</text></g>'
        )
    legend = [
        ("public_ready", "public ready"),
        ("usable_with_context", "context"),
        ("source_note_required", "single source"),
        ("lead_or_disputed", "lead/disputed"),
        ("internal_only", "internal"),
    ]
    legend_marks = []
    for idx, (key, label) in enumerate(legend):
        x = left + idx * 150
        y = height - 34
        legend_marks.append(
            f'<g><circle cx="{x}" cy="{y}" r="7" fill="{color_for(key)}"/>'
            f'<text x="{x + 14}" y="{y + 4}" class="mini-label">{html.escape(label)}</text></g>'
        )
    return (
        '<div class="chart-shell scroll-x">'
        f'<svg class="chart-svg" style="min-width:{width}px" viewBox="0 0 {width} {height}" role="img" aria-label="Layered knowledge graph v2">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        f'<text x="{left}" y="24" class="axis-label">Layered evidence navigation graph: node color reflects readiness/evidence state; dashed edges require caveats.</text>'
        f'{"".join(layer_guides)}{"".join(edge_marks)}{"".join(node_marks)}{"".join(legend_marks)}'
        "</svg></div>"
    )
