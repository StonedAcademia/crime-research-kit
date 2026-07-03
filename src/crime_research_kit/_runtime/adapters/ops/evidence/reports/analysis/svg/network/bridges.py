"""Bridge-flow SVG figure builders for analysis chart exports."""

from __future__ import annotations

from typing import Any

from crime_research_kit._runtime.core.models.reports import Group, Path, Rect, SvgDoc, SvgElement, Text

from crime_research_kit._runtime.adapters.ops.evidence.ledger.records import flatten
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.svg.base import color_for, short_label


def _chart_doc(width: int, height: int, label: str, elements: list[SvgElement]) -> SvgDoc:
    return SvgDoc(
        width=width, height=height, view_box=f"0 0 {width} {height}", css_class="chart-svg", role="img", aria_label=label,
        elements=[Rect(x=0, y=0, width=width, height=height, rx=8, css_class="chart-bg"), *elements],
    )


def _no_data_figure() -> SvgDoc:
    return _chart_doc(900, 220, "No chart data", [Text(x=450, y=112, content="No chart data", css_class="axis-label", anchor="middle")])


def build_sankey_figure(nodes: list[dict[str, Any]], links: list[dict[str, Any]]) -> SvgDoc:
    if not nodes or not links:
        return _no_data_figure()
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
    paths: list[SvgElement] = []
    for link in links:
        src = str(link.get("src_cluster", ""))
        dst = str(link.get("dst_cluster", ""))
        if src not in positions or dst not in positions:
            continue
        sx, sy = positions[src]
        dx, dy = positions[dst]
        color = color_for(link.get("public_readiness") or link.get("bridge_class"))
        stroke_width = 10 if link.get("public_readiness") != "lead_or_disputed" else 6
        paths.append(
            Path(
                d=f"M {sx + 128:.1f} {sy:.1f} C {(sx + dx) / 2:.1f} {sy:.1f}, {(sx + dx) / 2:.1f} {dy:.1f}, {dx:.1f} {dy:.1f}",
                fill="none",
                stroke=color,
                stroke_opacity="0.42",
                stroke_width=stroke_width,
                stroke_dasharray="7 5" if "category" in str(link.get("bridge_class", "")) or "lead" in str(link.get("bridge_class", "")) else "",
                title=flatten(link.get("path")),
            )
        )
    rects: list[SvgElement] = []
    for cluster_id, (x, y) in positions.items():
        node = node_by_id.get(cluster_id, {})
        label = f"{cluster_id}: {short_label(node.get('cluster_label'), 22)}"
        members = short_label(node.get("member_names"), 38)
        rects.append(
            Group(children=[
                Rect(x=f"{x:.1f}", y=f"{y - 24:.1f}", width=142, height=48, rx=7, css_class="node-box"),
                Text(x=f"{x + 10:.1f}", y=f"{y - 5:.1f}", content=label, css_class="node-label"),
                Text(x=f"{x + 10:.1f}", y=f"{y + 13:.1f}", content=members, css_class="mini-label"),
            ])
        )
    axis = Text(x=20, y=30, content="Audited inter-cluster bridge flow; dashed links are category/lead/context bridges.", css_class="axis-label")
    return _chart_doc(width, height, "Cluster bridge Sankey", [*paths, *rects, axis])
