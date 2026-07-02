"""Bridge-flow SVG renderers for analysis chart exports."""

from __future__ import annotations

import html
from typing import Any

from adapters.ops.evidence.reports.analysis.svg.base import color_for, html_title, short_label, svg_no_data


def render_sankey_svg(nodes: list[dict[str, Any]], links: list[dict[str, Any]]) -> str:
    if not nodes or not links:
        return svg_no_data()
    node_by_id = {str(row.get("cluster_id")): row for row in nodes}
    stage: dict[str, int] = {cluster_id: 0 for cluster_id in node_by_id}
    for _ in range(max(1, len(links))):
        changed = False
        for link in links:
            src = str(link.get("src_cluster", ""))
            dst = str(link.get("dst_cluster", ""))
            if src in stage and dst in stage and stage[dst] < stage[src] + 1:
                stage[dst] = stage[src] + 1
                changed = True
        if not changed:
            break
    stages: dict[int, list[str]] = {}
    for cluster_id, idx in stage.items():
        stages.setdefault(idx, []).append(cluster_id)
    width, height = 1120, 420
    max_stage = max(stages) if stages else 1
    positions: dict[str, tuple[float, float]] = {}
    for idx, cluster_ids in stages.items():
        ordered = sorted(cluster_ids)
        x = 80 + (width - 200) * (idx / max(1, max_stage))
        step = (height - 120) / max(1, len(ordered))
        for pos, cluster_id in enumerate(ordered):
            y = 70 + step * pos + step / 2
            positions[cluster_id] = (x, y)
    paths = []
    for link in links:
        src = str(link.get("src_cluster", ""))
        dst = str(link.get("dst_cluster", ""))
        if src not in positions or dst not in positions:
            continue
        sx, sy = positions[src]
        dx, dy = positions[dst]
        color = color_for(link.get("public_readiness") or link.get("bridge_class"))
        stroke_width = 10 if link.get("public_readiness") != "lead_or_disputed" else 6
        dash = " stroke-dasharray=\"7 5\"" if "category" in str(link.get("bridge_class", "")) or "lead" in str(link.get("bridge_class", "")) else ""
        paths.append(
            f'<path d="M {sx + 128:.1f} {sy:.1f} C {(sx + dx) / 2:.1f} {sy:.1f}, {(sx + dx) / 2:.1f} {dy:.1f}, {dx:.1f} {dy:.1f}" '
            f'fill="none" stroke="{color}" stroke-opacity="0.42" stroke-width="{stroke_width}"{dash}>{html_title(link.get("path"))}</path>'
        )
    rects = []
    for cluster_id, (x, y) in positions.items():
        node = node_by_id.get(cluster_id, {})
        label = f"{cluster_id}: {short_label(node.get('cluster_label'), 22)}"
        members = short_label(node.get("member_names"), 38)
        rects.append(
            f'<g><rect x="{x:.1f}" y="{y - 24:.1f}" width="142" height="48" rx="7" class="node-box"/>'
            f'<text x="{x + 10:.1f}" y="{y - 5:.1f}" class="node-label">{html.escape(label)}</text>'
            f'<text x="{x + 10:.1f}" y="{y + 13:.1f}" class="mini-label">{html.escape(members)}</text></g>'
        )
    return (
        '<div class="chart-shell">'
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Cluster bridge Sankey">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        f'{"".join(paths)}{"".join(rects)}'
        '<text x="20" y="30" class="axis-label">Audited inter-cluster bridge flow; dashed links are category/lead/context bridges.</text>'
        "</svg></div>"
    )
