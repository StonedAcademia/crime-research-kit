"""People cluster HTML renderer."""

from __future__ import annotations

import html
import math
from typing import Any

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
    width = 1280
    height = 820
    positions = _positions(width, height, nodes, cluster_by_id)
    edge_lines = _edge_lines(edges, positions)
    node_shapes = _node_shapes(nodes, positions, cluster_by_id, density_by_id)
    node_rows = _node_rows(nodes, cluster_by_id, density_by_id)
    edge_rows = _edge_rows(edges)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Leiden people clusters - {html.escape(case_title)}</title>
<style>
body {{ margin: 0; font-family: Arial, sans-serif; color: #1f2933; background: #f7f8fa; }}
main {{ max-width: 1420px; margin: 0 auto; padding: 28px; }}
h1 {{ font-size: 26px; margin: 0 0 6px; }}
p {{ max-width: 980px; line-height: 1.45; }}
.panel {{ background: #fff; border: 1px solid #d8dee6; border-radius: 8px; padding: 18px; margin-top: 18px; }}
svg {{ width: 100%; height: auto; background: #fbfcfe; border: 1px solid #d8dee6; border-radius: 8px; }}
.edge {{ stroke: #64748b; opacity: 0.78; }}
.node {{ fill: #ffffff; stroke-width: 4; }}
.node-label {{ fill: #111827; font-size: 13px; font-weight: 700; text-anchor: middle; }}
.node-sub {{ fill: #475569; font-size: 11px; text-anchor: middle; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ border-bottom: 1px solid #e2e8f0; padding: 8px; text-align: left; vertical-align: top; }}
th {{ background: #eef2f7; }}
</style>
</head>
<body>
<main>
<h1>Leiden people clusters</h1>
<p>{html.escape(case_title)}. Scope: {"public and internal rows" if include_private else "public-export rows only"}. Edge weights are evidence-weighted; node size is graph-kernel density. Dashed edges include weak co-mentions and should be treated as leads only.</p>
<section class="panel">
<svg viewBox="0 0 {width} {height}" role="img" aria-label="Leiden people clusters">
{''.join(edge_lines)}
{''.join(node_shapes)}
</svg>
</section>
<section class="panel">
<h2>Clustered People</h2>
<table>
<thead><tr><th>Cluster</th><th>Person</th><th>KDE</th><th>Status</th><th>Public Export</th></tr></thead>
<tbody>{node_rows}</tbody>
</table>
</section>
<section class="panel">
<h2>Weighted Edges</h2>
<table>
<thead><tr><th>Person</th><th>Person</th><th>Weight</th><th>Connection</th><th>Status</th></tr></thead>
<tbody>{edge_rows}</tbody>
</table>
</section>
</main>
</body>
</html>
"""


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
            if len(members) == 1:
                x, y = cluster_x, cluster_y
            else:
                member_angle = (2 * math.pi * member_idx / len(members)) - (math.pi / 2)
                x = cluster_x + member_radius * math.cos(member_angle)
                y = cluster_y + member_radius * math.sin(member_angle)
            positions[str(node["entity_id"])] = (x, y)
    return positions


def _edge_lines(edges: list[dict[str, Any]], positions: dict[str, tuple[float, float]]) -> list[str]:
    lines = []
    for edge in edges:
        src = str(edge["src_entity_id"])
        dst = str(edge["dst_entity_id"])
        if src not in positions or dst not in positions:
            continue
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        weight = parse_float(edge.get("edge_weight"), 0.0)
        dashed = "stroke-dasharray:6 6;" if "co_mentioned_with" in parse_cell_list(edge.get("connection_types")) else ""
        lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="edge" style="stroke-width:{0.75 + (weight * 4):.2f};{dashed}" />')
    return lines


def _node_shapes(nodes: list[dict[str, Any]], positions: dict[str, tuple[float, float]], cluster_by_id: dict[str, str], density_by_id: dict[str, float]) -> list[str]:
    colors = ["#2563eb", "#0f766e", "#7c3aed", "#b45309", "#be123c", "#475569", "#15803d", "#0369a1"]
    shapes = []
    for node in nodes:
        entity_id = str(node["entity_id"])
        x, y = positions[entity_id]
        cluster_id = cluster_by_id[entity_id]
        color = colors[(int(cluster_id[1:]) - 1) % len(colors)] if cluster_id[1:].isdigit() else colors[0]
        density = density_by_id.get(entity_id, 0.0)
        radius = 24 + min(16, density * 18)
        label = truncate_label(entity_display(node), 24)
        shapes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" class="node" style="stroke:{color};" />' f'<text x="{x:.1f}" y="{y + radius + 18:.1f}" class="node-label">{html.escape(label)}</text>' f'<text x="{x:.1f}" y="{y + radius + 34:.1f}" class="node-sub">{html.escape(cluster_id)} kde={density:.2f}</text>')
    return shapes


def _node_rows(nodes: list[dict[str, Any]], cluster_by_id: dict[str, str], density_by_id: dict[str, float]) -> str:
    return "\n".join("<tr>" f"<td>{html.escape(cluster_by_id[str(node['entity_id'])])}</td>" f"<td>{html.escape(entity_display(node))}</td>" f"<td>{density_by_id.get(str(node['entity_id']), 0.0):.6f}</td>" f"<td>{html.escape(str(node.get('status', '')))}</td>" f"<td>{html.escape(str(node.get('public_export', '')))}</td>" "</tr>" for node in sorted(nodes, key=lambda row: (cluster_by_id[str(row["entity_id"])], entity_display(row))))


def _edge_rows(edges: list[dict[str, Any]]) -> str:
    return "\n".join("<tr>" f"<td>{html.escape(str(edge.get('src_name', '')))}</td>" f"<td>{html.escape(str(edge.get('dst_name', '')))}</td>" f"<td>{html.escape(str(edge.get('edge_weight', '')))}</td>" f"<td>{html.escape(str(edge.get('connection_types', '')))}</td>" f"<td>{html.escape(str(edge.get('statuses', '')))}</td>" "</tr>" for edge in sorted(edges, key=lambda row: (str(row.get("src_name", "")), str(row.get("dst_name", "")))))
