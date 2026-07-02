"""People graph HTML renderer."""

from __future__ import annotations

import html
import math
from typing import Any

from adapters.ops.evidence.reports.common import (
    edge_evidence_label,
    edge_is_lead_only,
    entity_display,
    people_graph_groups,
    truncate_label,
)
from adapters.ops.evidence.reports.weights import evidence_edge_weight, parse_float
from adapters.ops.evidence.shared.records import flatten


def render_people_graph_html(
    case_title: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    include_private: bool,
) -> str:
    width = 1320
    height = max(820, 650 + (len(nodes) * 7))
    cx = width / 2
    cy = height / 2
    colors = ["#2563eb", "#0f766e", "#7c3aed", "#b45309", "#be123c", "#475569", "#15803d", "#0369a1"]
    weighted_edges = []
    for edge in edges:
        row = dict(edge)
        row["edge_weight"] = evidence_edge_weight(row)
        weighted_edges.append(row)

    group_by_id, groups = people_graph_groups(nodes, weighted_edges)
    degree = {str(node.get("entity_id", "")): 0 for node in nodes}
    weighted_degree = {str(node.get("entity_id", "")): 0.0 for node in nodes}
    for edge in weighted_edges:
        weight = parse_float(edge.get("edge_weight"), 0.0)
        for node_id in [str(edge.get("src_entity_id", "")), str(edge.get("dst_entity_id", ""))]:
            if node_id in degree:
                degree[node_id] += 1
                weighted_degree[node_id] += weight

    positions = _positions(width, height, nodes, groups)
    edge_lines = _edge_lines(weighted_edges, positions)
    node_shapes = _node_shapes(nodes, positions, group_by_id, degree, weighted_degree, colors)
    group_rows = _group_rows(groups)
    node_rows = _node_rows(nodes, group_by_id, degree, weighted_degree)
    edge_rows = _edge_rows(weighted_edges)
    strong_edges = sum(1 for edge in weighted_edges if parse_float(edge.get("edge_weight"), 0.0) >= 0.7)
    lead_edges = sum(1 for edge in weighted_edges if edge_is_lead_only(edge))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Evidence-weighted people graph - {html.escape(case_title)}</title>
<style>
body {{ margin: 0; font-family: Arial, sans-serif; color: #1f2933; background: #f7f8fa; }}
main {{ max-width: 1420px; margin: 0 auto; padding: 28px; }}
h1 {{ font-size: 26px; margin: 0 0 6px; }}
h2 {{ font-size: 18px; margin: 0 0 14px; }}
p {{ max-width: 1080px; line-height: 1.45; }}
.summary {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }}
.metric {{ background: #fff; border: 1px solid #d8dee6; border-radius: 8px; padding: 14px; }}
.metric strong {{ display: block; font-size: 22px; margin-bottom: 4px; }}
.metric span {{ color: #475569; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
.panel {{ background: #fff; border: 1px solid #d8dee6; border-radius: 8px; padding: 18px; margin-top: 18px; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 14px 0 0; color: #475569; font-size: 13px; }}
.legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
.swatch {{ width: 22px; height: 0; border-top: 4px solid #1d4ed8; display: inline-block; }}
.swatch.medium {{ border-color: #64748b; }}
.swatch.weak {{ border-color: #94a3b8; border-top-style: dashed; }}
svg {{ width: 100%; height: auto; background: #fbfcfe; border: 1px solid #d8dee6; border-radius: 8px; }}
.edge {{ opacity: 0.82; }}
.node {{ stroke-width: 4; }}
.node-label {{ fill: #111827; font-size: 13px; font-weight: 700; text-anchor: middle; }}
.node-sub {{ fill: #475569; font-size: 11px; text-anchor: middle; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ border-bottom: 1px solid #e2e8f0; padding: 8px; text-align: left; vertical-align: top; }}
th {{ background: #eef2f7; }}
@media (max-width: 860px) {{
  main {{ padding: 16px; }}
  .summary {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  table {{ font-size: 12px; }}
}}
</style>
</head>
<body>
<main>
<h1>Evidence-weighted people graph</h1>
<p>{html.escape(case_title)}. Scope: {"public and internal rows" if include_private else "public-export rows only"}. Edges are source-bound direct person-person relationships or shared event/context links; contextual links do not imply direct participation.</p>
<div class="summary">
<div class="metric"><strong>{len(nodes)}</strong><span>People</span></div>
<div class="metric"><strong>{len(weighted_edges)}</strong><span>Edges</span></div>
<div class="metric"><strong>{len(groups)}</strong><span>Connected groups</span></div>
<div class="metric"><strong>{strong_edges}/{lead_edges}</strong><span>Strong / lead edges</span></div>
</div>
<section class="panel">
<svg viewBox="0 0 {width} {height}" role="img" aria-label="People-only connection graph">
{''.join(edge_lines)}
{''.join(node_shapes)}
</svg>
<div class="legend">
<span><i class="swatch"></i> higher-weight evidence edge</span>
<span><i class="swatch medium"></i> medium evidence edge</span>
<span><i class="swatch weak"></i> lead/context edge</span>
<span>Node outline color marks graph group; node size follows weighted degree.</span>
</div>
</section>
<section class="panel">
<h2>Graph Groups</h2>
<table>
<thead><tr><th>Group</th><th>People</th><th>Members</th></tr></thead>
<tbody>{group_rows}</tbody>
</table>
</section>
<section class="panel">
<h2>People</h2>
<table>
<thead><tr><th>Group</th><th>Person</th><th>Status</th><th>Degree</th><th>Weighted Degree</th><th>Roles</th><th>Sources</th></tr></thead>
<tbody>{node_rows}</tbody>
</table>
</section>
<section class="panel">
<h2>Edges</h2>
<table>
<thead><tr><th>Person</th><th>Person</th><th>Evidence</th><th>Weight</th><th>Status</th><th>Confidence</th><th>Connection</th><th>Events</th><th>Claims</th><th>Sources</th></tr></thead>
<tbody>
{edge_rows}
</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def _positions(width: int, height: int, nodes: list[dict[str, Any]], groups: list[list[dict[str, Any]]]) -> dict[str, tuple[float, float]]:
    positions: dict[str, tuple[float, float]] = {}
    cx = width / 2
    cy = height / 2
    for group_idx, group in enumerate(groups):
        if len(groups) == 1:
            group_x, group_y = cx, cy
        else:
            angle = (2 * math.pi * group_idx / max(1, len(groups))) - (math.pi / 2)
            group_x = cx + 440 * math.cos(angle)
            group_y = cy + 255 * math.sin(angle)
        member_radius = 0 if len(group) == 1 else min(96, 46 + (len(group) * 10))
        for member_idx, node in enumerate(group):
            if len(group) == 1:
                x, y = group_x, group_y
            else:
                member_angle = (2 * math.pi * member_idx / len(group)) - (math.pi / 2)
                x = group_x + member_radius * math.cos(member_angle)
                y = group_y + member_radius * math.sin(member_angle)
            positions[str(node["entity_id"])] = (x, y)
    return positions


def _edge_lines(weighted_edges: list[dict[str, Any]], positions: dict[str, tuple[float, float]]) -> list[str]:
    edge_lines = []
    for edge in weighted_edges:
        src = str(edge["src_entity_id"])
        dst = str(edge["dst_entity_id"])
        if src not in positions or dst not in positions:
            continue
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        weight = parse_float(edge.get("edge_weight"), 0.0)
        dashed = "stroke-dasharray:7 7;" if edge_is_lead_only(edge) else ""
        stroke = "#1d4ed8" if weight >= 0.7 else "#64748b" if weight >= 0.35 else "#94a3b8"
        title = f"{edge.get('src_name', src)} - {edge.get('dst_name', dst)} | {flatten(edge.get('connection_types'))} | status={flatten(edge.get('statuses')) or 'unknown'} | weight={weight:.2f}"
        edge_lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="edge" style="stroke:{stroke};stroke-width:{1.2 + (weight * 4):.2f};{dashed}"><title>{html.escape(title)}</title></line>')
    return edge_lines


def _node_shapes(nodes: list[dict[str, Any]], positions: dict[str, tuple[float, float]], group_by_id: dict[str, str], degree: dict[str, int], weighted_degree: dict[str, float], colors: list[str]) -> list[str]:
    node_shapes = []
    for node in nodes:
        entity_id = str(node["entity_id"])
        x, y = positions[entity_id]
        group_id = group_by_id.get(entity_id, "G?")
        group_num = int(group_id[1:]) if group_id[1:].isdigit() else 1
        color = colors[(group_num - 1) % len(colors)]
        node_radius = 29 + min(12, weighted_degree.get(entity_id, 0.0) * 5)
        label = truncate_label(entity_display(node), 24)
        sub = truncate_label(f"{group_id} | {node.get('status', 'unknown')} | deg {degree.get(entity_id, 0)}", 34)
        fill = "#fff7ed" if node.get("public_export", True) is False else "#ffffff"
        title = f"{entity_display(node)} | group={group_id} | roles={flatten(node.get('role_tags'))} | claims={flatten(node.get('claim_ids'))} | sources={flatten(node.get('source_ids'))}"
        node_shapes.append("<g>" f"<title>{html.escape(title)}</title>" f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{node_radius:.1f}" class="node" style="stroke:{color};fill:{fill};" />' f'<text x="{x:.1f}" y="{y + node_radius + 18:.1f}" class="node-label">{html.escape(label)}</text>' f'<text x="{x:.1f}" y="{y + node_radius + 34:.1f}" class="node-sub">{html.escape(sub)}</text>' "</g>")
    return node_shapes


def _group_rows(groups: list[list[dict[str, Any]]]) -> str:
    return "\n".join("<tr>" f"<td>G{idx}</td>" f"<td>{len(group)}</td>" f"<td>{html.escape('; '.join(entity_display(node) for node in group))}</td>" "</tr>" for idx, group in enumerate(groups, start=1))


def _node_rows(nodes: list[dict[str, Any]], group_by_id: dict[str, str], degree: dict[str, int], weighted_degree: dict[str, float]) -> str:
    return "\n".join("<tr>" f"<td>{html.escape(group_by_id.get(str(node.get('entity_id')), ''))}</td>" f"<td>{html.escape(entity_display(node))}</td>" f"<td>{html.escape(str(node.get('status', '')))}</td>" f"<td>{degree.get(str(node.get('entity_id')), 0)}</td>" f"<td>{weighted_degree.get(str(node.get('entity_id')), 0.0):.2f}</td>" f"<td>{html.escape(flatten(node.get('role_tags')))}</td>" f"<td>{html.escape(flatten(node.get('source_ids')))}</td>" "</tr>" for node in sorted(nodes, key=lambda row: (group_by_id.get(str(row.get("entity_id")), ""), entity_display(row))))


def _edge_rows(weighted_edges: list[dict[str, Any]]) -> str:
    return "\n".join("<tr>" f"<td>{html.escape(edge['src_name'])}</td>" f"<td>{html.escape(edge['dst_name'])}</td>" f"<td>{html.escape(edge_evidence_label(edge))}</td>" f"<td>{edge.get('edge_weight', 0):.2f}</td>" f"<td>{html.escape(flatten(edge.get('statuses')))}</td>" f"<td>{html.escape(str(edge.get('confidence', '')))}</td>" f"<td>{html.escape(flatten(edge.get('connection_types')))}</td>" f"<td>{html.escape(flatten(edge.get('event_ids')))}</td>" f"<td>{html.escape(flatten(edge.get('claim_ids')))}</td>" f"<td>{html.escape(flatten(edge.get('source_ids')))}</td>" "</tr>" for edge in sorted(weighted_edges, key=lambda row: (-parse_float(row.get("edge_weight"), 0.0), row["src_name"], row["dst_name"])))
