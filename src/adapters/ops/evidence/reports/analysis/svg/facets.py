"""Specialty SVG figure builders for analysis chart exports."""

from __future__ import annotations

import math
from typing import Any

from core.models.reports import Circle, Group, Line, Path, Rect, SvgDoc, SvgElement, Text

from adapters.ops.evidence.ledger.records import flatten
from adapters.ops.evidence.reports.analysis.pages.render import render_svg_doc
from adapters.ops.evidence.reports.analysis.svg.base import color_for, parse_year, short_label
from adapters.ops.evidence.reports.weights import parse_float


def _chart_doc(width: int, height: int, label: str, elements: list[SvgElement], style: str = "") -> SvgDoc:
    return SvgDoc(
        width=width, height=height, view_box=f"0 0 {width} {height}", css_class="chart-svg", style=style, role="img", aria_label=label,
        elements=[Rect(x=0, y=0, width=width, height=height, rx=8, css_class="chart-bg"), *elements],
    )


def _no_data_figure() -> SvgDoc:
    return _chart_doc(900, 220, "No chart data", [Text(x=450, y=112, content="No chart data", css_class="axis-label", anchor="middle")])


def build_path_atlas_figure(rows: list[dict[str, Any]]) -> SvgDoc:
    if not rows:
        return _no_data_figure()
    display = rows[:22]
    max_hops = max((int(row.get("hops") or 0) for row in display), default=1)
    width, height = 1080, 80 + 30 * len(display)
    left, right = 180, 42
    lane_width = width - left - right
    parts: list[SvgElement] = []
    for hop in range(max_hops + 1):
        x = left + lane_width * hop / max(1, max_hops)
        parts.append(Line(x1=f"{x:.1f}", y1=42, x2=f"{x:.1f}", y2=height - 28, stroke="#e1e8ef"))
        parts.append(Text(x=f"{x:.1f}", y=30, content=str(hop), css_class="mini-label", anchor="middle"))
    for idx, row in enumerate(display):
        y = 62 + idx * 30
        hops = int(row.get("hops") or 0)
        end_x = left + lane_width * hops / max(1, max_hops)
        color = color_for("lead_or_disputed" if str(row.get("over_six_hops")) == "True" else row.get("weakest_status"), idx)
        parts.append(Text(x=left - 12, y=y + 4, content=short_label(row.get("target_person"), 24), css_class="mini-label", anchor="end"))
        parts.append(Line(x1=left, y1=y, x2=f"{end_x:.1f}", y2=y, stroke=color, stroke_width=4, stroke_opacity="0.65", title=flatten(row.get("path"))))
        for hop in range(hops + 1):
            x = left + lane_width * hop / max(1, max_hops)
            parts.append(Circle(cx=f"{x:.1f}", cy=y, r=4, fill=color))
        if str(row.get("over_six_hops")) == "True":
            parts.append(Text(x=f"{end_x + 9:.1f}", y=y + 4, content=">6", css_class="warn-label"))
    axis = Text(x=f"{left + lane_width / 2:.1f}", y=height - 8, content="hops from anchor", css_class="axis-label", anchor="middle")
    return _chart_doc(width, height, "6DOF path atlas", [axis, *parts], style=f"min-width:{width}px")


def render_path_atlas_svg(rows: list[dict[str, Any]]) -> str:
    return render_svg_doc(build_path_atlas_figure(rows))


def build_boundary_overlay_figure(rows: list[dict[str, Any]]) -> SvgDoc:
    if not rows:
        return _no_data_figure()
    record_types = sorted({str(row.get("record_type") or "record") for row in rows})
    statuses = sorted({str(row.get("status") or "unknown") for row in rows})
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (str(row.get("record_type") or "record"), str(row.get("status") or "unknown"))
        counts[key] = counts.get(key, 0) + 1
    width, height = 920, 120 + 70 * len(record_types)
    left, top = 150, 62
    x_step = (width - left - 54) / max(1, len(statuses) - 1)
    max_count = max(counts.values(), default=1)
    bubbles: list[SvgElement] = []
    for r_idx, record_type in enumerate(record_types):
        y = top + r_idx * 70
        bubbles.append(Text(x=left - 14, y=y + 5, content=record_type, css_class="node-label", anchor="end"))
        for s_idx, status in enumerate(statuses):
            count = counts.get((record_type, status), 0)
            if count:
                x = left + s_idx * x_step
                radius = 7 + 22 * math.sqrt(count / max_count)
                bubbles.extend([
                    Circle(cx=f"{x:.1f}", cy=y, r=f"{radius:.1f}", fill=color_for(status, s_idx), fill_opacity="0.72", title=f"{record_type} / {status}: {count}"),
                    Text(x=f"{x:.1f}", y=y + 4, content=str(count), css_class="heat-label", anchor="middle"),
                ])
    headers = [Text(x=f"{left + idx * x_step:.1f}", y=36, content=short_label(status, 16), css_class="mini-label", anchor="middle") for idx, status in enumerate(statuses)]
    return _chart_doc(width, height, "Contradiction and boundary overlay", [*headers, *bubbles], style=f"min-width:{width}px")


def render_boundary_overlay_svg(rows: list[dict[str, Any]]) -> str:
    return render_svg_doc(build_boundary_overlay_figure(rows))


def build_swimlanes_figure(rows: list[dict[str, Any]]) -> SvgDoc:
    dated = [row for row in rows if parse_year(row.get("start_date")) is not None]
    if not dated:
        return _no_data_figure()
    years = [parse_year(row.get("start_date")) for row in dated]
    min_year = min(year for year in years if year is not None)
    max_year = max(year for year in years if year is not None)
    lanes = sorted({str(row.get("cluster_id") or "unclustered") for row in dated})[:12]
    width, height = 1120, 96 + 54 * len(lanes)
    left, right, top = 156, 44, 68
    lane_width = width - left - right
    parts: list[SvgElement] = []
    for idx, lane in enumerate(lanes):
        y = top + idx * 54
        parts.append(Line(x1=left, y1=y, x2=width - right, y2=y, stroke="#d9e1e8"))
        parts.append(Text(x=left - 14, y=y + 4, content=lane, css_class="node-label", anchor="end"))
    for tick in range(7):
        year = min_year + (max_year - min_year) * tick / 6
        x = left + lane_width * tick / 6
        parts.append(Line(x1=f"{x:.1f}", y1=46, x2=f"{x:.1f}", y2=height - 30, stroke="#edf2f7"))
        parts.append(Text(x=f"{x:.1f}", y=34, content=str(int(year)), css_class="mini-label", anchor="middle"))
    for row in dated:
        lane = str(row.get("cluster_id") or "unclustered")
        if lane not in lanes:
            continue
        year = parse_year(row.get("start_date"))
        assert year is not None
        x = left + lane_width * (year - min_year) / max(1, max_year - min_year)
        y = top + lanes.index(lane) * 54
        parts.append(Circle(cx=f"{x:.1f}", cy=y, r=5.5, fill=color_for(row.get("event_link_status") or row.get("status")), fill_opacity="0.82", title=flatten(row.get("event_title"))))
    return _chart_doc(width, height, "Temporal cluster swimlanes", parts)


def render_swimlanes_svg(rows: list[dict[str, Any]]) -> str:
    return render_svg_doc(build_swimlanes_figure(rows))


def build_treemap_figure(rows: list[dict[str, Any]]) -> SvgDoc:
    if not rows:
        return _no_data_figure()
    display = rows[:36]
    family_totals: dict[str, float] = {}
    for row in display:
        family = str(row.get("relation_family") or "other")
        family_totals[family] = family_totals.get(family, 0.0) + parse_float(row.get("weighted_count"), 0.0)
    width, height = 1040, 430
    x, y, chart_w, chart_h = 24, 38, width - 48, height - 62
    total = sum(family_totals.values()) or 1.0
    rects: list[SvgElement] = []
    x_cursor = x
    for f_idx, (family, family_value) in enumerate(sorted(family_totals.items(), key=lambda item: -item[1])):
        family_w = chart_w * family_value / total
        family_rows = [row for row in display if str(row.get("relation_family") or "other") == family]
        child_total = sum(parse_float(row.get("weighted_count"), 0.0) for row in family_rows) or 1.0
        y_cursor = y
        rects.append(Text(x=f"{x_cursor + 5:.1f}", y=f"{y_cursor - 8:.1f}", content=short_label(family, 24), css_class="mini-label"))
        for row in family_rows:
            value = parse_float(row.get("weighted_count"), 0.0)
            child_h = chart_h * value / child_total
            color = color_for(row.get("status"), f_idx)
            label_len = int(max(8, family_w / 8))
            rects.append(Group(title=f"{row.get('relation_type')} / weight {value}", children=[
                Rect(x=f"{x_cursor:.1f}", y=f"{y_cursor:.1f}", width=f"{max(1, family_w - 4):.1f}", height=f"{max(1, child_h - 3):.1f}", rx=4, fill=color, fill_opacity="0.74", stroke="#fff"),
                Text(x=f"{x_cursor + 6:.1f}", y=f"{y_cursor + 16:.1f}", content=short_label(row.get("relation_type"), label_len), css_class="treemap-label"),
            ]))
            y_cursor += child_h
        x_cursor += family_w
    return _chart_doc(width, height, "Relationship type treemap", rects, style=f"min-width:{width}px")


def render_treemap_svg(rows: list[dict[str, Any]]) -> str:
    return render_svg_doc(build_treemap_figure(rows))


def build_bipartite_figure(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> SvgDoc:
    if not nodes or not edges:
        return _no_data_figure()
    people = sorted((row for row in nodes if row.get("node_type") == "person"), key=lambda row: -parse_float(row.get("degree"), 0.0))[:16]
    sources = sorted((row for row in nodes if row.get("node_type") == "source"), key=lambda row: -parse_float(row.get("degree"), 0.0))[:20]
    people_ids = {str(row.get("entity_id")) for row in people}
    source_ids = {str(row.get("source_id")) for row in sources}
    width, height = 1080, max(520, 74 + 24 * max(len(people), len(sources)))
    left_x, right_x = 250, 820
    people_pos = {str(row.get("entity_id")): (left_x, 58 + idx * 28) for idx, row in enumerate(people)}
    source_pos = {str(row.get("source_id")): (right_x, 58 + idx * 24) for idx, row in enumerate(sources)}
    paths: list[SvgElement] = []
    for edge in edges:
        pid = str(edge.get("person_id"))
        sid = str(edge.get("source_id"))
        if pid in people_ids and sid in source_ids:
            sx, sy = people_pos[pid]
            dx, dy = source_pos[sid]
            paths.append(Path(d=f"M {sx + 8} {sy} C 455 {sy}, 610 {dy}, {dx - 8} {dy}", fill="none", stroke=color_for(edge.get("source_grade")), stroke_width=1.2, stroke_opacity="0.18", title=flatten(edge.get("contexts"))))
    labels: list[SvgElement] = []
    for row in people:
        x0, y0 = people_pos[str(row.get("entity_id"))]
        labels.append(Circle(cx=x0, cy=y0, r=6, fill="#2b6cb0"))
        labels.append(Text(x=x0 - 12, y=y0 + 4, content=short_label(row.get("label"), 28), css_class="mini-label", anchor="end"))
    for row in sources:
        x0, y0 = source_pos[str(row.get("source_id"))]
        labels.append(Circle(cx=x0, cy=y0, r=5, fill=color_for(row.get("reliability_grade"))))
        labels.append(Text(x=x0 + 12, y=y0 + 4, content=short_label(row.get("label"), 36), css_class="mini-label"))
    axes = [Text(x=250, y=30, content="people", css_class="axis-label", anchor="middle"), Text(x=820, y=30, content="sources", css_class="axis-label", anchor="middle")]
    return _chart_doc(width, height, "Person source bipartite graph", [*axes, *paths, *labels], style=f"min-width:{width}px")


def render_bipartite_svg(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    return render_svg_doc(build_bipartite_figure(nodes, edges))
