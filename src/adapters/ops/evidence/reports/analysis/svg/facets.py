"""Specialty SVG renderers for analysis chart exports."""

from __future__ import annotations

import html
import math
from typing import Any

from adapters.ops.evidence.reports.analysis.svg.base import (
    color_for,
    html_title,
    parse_year,
    short_label,
    svg_no_data,
)
from adapters.ops.evidence.reports.weights import parse_float


def render_path_atlas_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return svg_no_data()
    display = rows[:22]
    max_hops = max((int(row.get("hops") or 0) for row in display), default=1)
    width, height = 1080, 80 + 30 * len(display)
    left, right = 180, 42
    lane_width = width - left - right
    parts = []
    for hop in range(max_hops + 1):
        x = left + lane_width * hop / max(1, max_hops)
        parts.append(f'<line x1="{x:.1f}" y1="42" x2="{x:.1f}" y2="{height - 28}" stroke="#e1e8ef" stroke-width="1"/>')
        parts.append(f'<text x="{x:.1f}" y="30" class="mini-label" text-anchor="middle">{hop}</text>')
    for idx, row in enumerate(display):
        y = 62 + idx * 30
        hops = int(row.get("hops") or 0)
        end_x = left + lane_width * hops / max(1, max_hops)
        color = color_for("lead_or_disputed" if str(row.get("over_six_hops")) == "True" else row.get("weakest_status"), idx)
        parts.append(f'<text x="{left - 12}" y="{y + 4}" class="mini-label" text-anchor="end">{html.escape(short_label(row.get("target_person"), 24))}</text>')
        parts.append(f'<line x1="{left}" y1="{y}" x2="{end_x:.1f}" y2="{y}" stroke="{color}" stroke-width="4" stroke-opacity="0.65">{html_title(row.get("path"))}</line>')
        for hop in range(hops + 1):
            x = left + lane_width * hop / max(1, max_hops)
            parts.append(f'<circle cx="{x:.1f}" cy="{y}" r="4" fill="{color}"/>')
        if str(row.get("over_six_hops")) == "True":
            parts.append(f'<text x="{end_x + 9:.1f}" y="{y + 4}" class="warn-label">&gt;6</text>')
    return (
        '<div class="chart-shell scroll-x">'
        f'<svg class="chart-svg" style="min-width:{width}px" viewBox="0 0 {width} {height}" role="img" aria-label="6DOF path atlas">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        f'<text x="{left + lane_width / 2:.1f}" y="{height - 8}" class="axis-label" text-anchor="middle">hops from anchor</text>'
        f'{"".join(parts)}</svg></div>'
    )


def render_boundary_overlay_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return svg_no_data()
    record_types = sorted({str(row.get("record_type") or "record") for row in rows})
    statuses = sorted({str(row.get("status") or "unknown") for row in rows})
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (str(row.get("record_type") or "record"), str(row.get("status") or "unknown"))
        counts[key] = counts.get(key, 0) + 1
    width, height = 920, 120 + 70 * len(record_types)
    left, top = 150, 62
    x_step = (width - left - 54) / max(1, len(statuses) - 1)
    y_step = 70
    max_count = max(counts.values(), default=1)
    bubbles = []
    for r_idx, record_type in enumerate(record_types):
        y = top + r_idx * y_step
        bubbles.append(f'<text x="{left - 14}" y="{y + 5}" class="node-label" text-anchor="end">{html.escape(record_type)}</text>')
        for s_idx, status in enumerate(statuses):
            count = counts.get((record_type, status), 0)
            if not count:
                continue
            x = left + s_idx * x_step
            radius = 7 + 22 * math.sqrt(count / max_count)
            bubbles.append(f'<circle cx="{x:.1f}" cy="{y}" r="{radius:.1f}" fill="{color_for(status, s_idx)}" fill-opacity="0.72">{html_title(f"{record_type} / {status}: {count}")}</circle><text x="{x:.1f}" y="{y + 4}" class="heat-label" text-anchor="middle">{count}</text>')
    headers = "".join(f'<text x="{left + idx * x_step:.1f}" y="36" class="mini-label" text-anchor="middle">{html.escape(short_label(status, 16))}</text>' for idx, status in enumerate(statuses))
    return (
        '<div class="chart-shell scroll-x">'
        f'<svg class="chart-svg" style="min-width:{width}px" viewBox="0 0 {width} {height}" role="img" aria-label="Contradiction and boundary overlay">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>{headers}{"".join(bubbles)}</svg></div>'
    )


def render_swimlanes_svg(rows: list[dict[str, Any]]) -> str:
    dated = [row for row in rows if parse_year(row.get("start_date")) is not None]
    if not dated:
        return svg_no_data()
    years = [parse_year(row.get("start_date")) for row in dated]
    min_year = min(year for year in years if year is not None)
    max_year = max(year for year in years if year is not None)
    lanes = sorted({str(row.get("cluster_id") or "unclustered") for row in dated})[:12]
    width, height = 1120, 96 + 54 * len(lanes)
    left, right, top = 156, 44, 68
    lane_width = width - left - right
    parts = []
    for idx, lane in enumerate(lanes):
        y = top + idx * 54
        parts.append(f'<line x1="{left}" y1="{y}" x2="{width - right}" y2="{y}" stroke="#d9e1e8" stroke-width="1"/>')
        parts.append(f'<text x="{left - 14}" y="{y + 4}" class="node-label" text-anchor="end">{html.escape(lane)}</text>')
    ticks = 6
    for tick in range(ticks + 1):
        year = min_year + (max_year - min_year) * tick / max(1, ticks)
        x = left + lane_width * tick / max(1, ticks)
        parts.append(f'<line x1="{x:.1f}" y1="46" x2="{x:.1f}" y2="{height - 30}" stroke="#edf2f7" stroke-width="1"/>')
        parts.append(f'<text x="{x:.1f}" y="34" class="mini-label" text-anchor="middle">{int(year)}</text>')
    for row in dated:
        lane = str(row.get("cluster_id") or "unclustered")
        if lane not in lanes:
            continue
        year = parse_year(row.get("start_date"))
        assert year is not None
        x = left + lane_width * (year - min_year) / max(1, max_year - min_year)
        y = top + lanes.index(lane) * 54
        color = color_for(row.get("event_link_status") or row.get("status"))
        parts.append(f'<circle cx="{x:.1f}" cy="{y}" r="5.5" fill="{color}" fill-opacity="0.82">{html_title(row.get("event_title"))}</circle>')
    return (
        '<div class="chart-shell">'
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Temporal cluster swimlanes">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>{"".join(parts)}</svg></div>'
    )


def render_treemap_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return svg_no_data()
    display = rows[:36]
    family_totals: dict[str, float] = {}
    for row in display:
        family = str(row.get("relation_family") or "other")
        family_totals[family] = family_totals.get(family, 0.0) + parse_float(row.get("weighted_count"), 0.0)
    width, height = 1040, 430
    x, y, chart_w, chart_h = 24, 38, width - 48, height - 62
    total = sum(family_totals.values()) or 1.0
    rects = []
    x_cursor = x
    for f_idx, (family, family_value) in enumerate(sorted(family_totals.items(), key=lambda item: -item[1])):
        family_w = chart_w * family_value / total
        family_rows = [row for row in display if str(row.get("relation_family") or "other") == family]
        child_total = sum(parse_float(row.get("weighted_count"), 0.0) for row in family_rows) or 1.0
        y_cursor = y
        rects.append(f'<text x="{x_cursor + 5:.1f}" y="{y_cursor - 8:.1f}" class="mini-label">{html.escape(short_label(family, 24))}</text>')
        for row in family_rows:
            value = parse_float(row.get("weighted_count"), 0.0)
            child_h = chart_h * value / child_total
            color = color_for(row.get("status"), f_idx)
            title = f"{row.get('relation_type')} / weight {value}"
            rects.append(
                f'<g><rect x="{x_cursor:.1f}" y="{y_cursor:.1f}" width="{max(1, family_w - 4):.1f}" height="{max(1, child_h - 3):.1f}" rx="4" fill="{color}" fill-opacity="0.74" stroke="#fff"/>'
                f'<text x="{x_cursor + 6:.1f}" y="{y_cursor + 16:.1f}" class="treemap-label">{html.escape(short_label(row.get("relation_type"), int(max(8, family_w / 8))))}</text>'
                f'{html_title(title)}</g>'
            )
            y_cursor += child_h
        x_cursor += family_w
    return (
        '<div class="chart-shell scroll-x">'
        f'<svg class="chart-svg" style="min-width:{width}px" viewBox="0 0 {width} {height}" role="img" aria-label="Relationship type treemap">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>{"".join(rects)}</svg></div>'
    )


def render_bipartite_svg(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    if not nodes or not edges:
        return svg_no_data()
    people = [row for row in nodes if row.get("node_type") == "person"]
    sources = [row for row in nodes if row.get("node_type") == "source"]
    people = sorted(people, key=lambda row: -parse_float(row.get("degree"), 0.0))[:16]
    sources = sorted(sources, key=lambda row: -parse_float(row.get("degree"), 0.0))[:20]
    people_ids = {str(row.get("entity_id")) for row in people}
    source_ids = {str(row.get("source_id")) for row in sources}
    width, height = 1080, max(520, 74 + 24 * max(len(people), len(sources)))
    left_x, right_x = 250, 820
    people_pos = {str(row.get("entity_id")): (left_x, 58 + idx * 28) for idx, row in enumerate(people)}
    source_pos = {str(row.get("source_id")): (right_x, 58 + idx * 24) for idx, row in enumerate(sources)}
    paths = []
    for edge in edges:
        pid = str(edge.get("person_id"))
        sid = str(edge.get("source_id"))
        if pid not in people_ids or sid not in source_ids:
            continue
        sx, sy = people_pos[pid]
        dx, dy = source_pos[sid]
        paths.append(f'<path d="M {sx + 8} {sy} C 455 {sy}, 610 {dy}, {dx - 8} {dy}" fill="none" stroke="{color_for(edge.get("source_grade"))}" stroke-width="1.2" stroke-opacity="0.18">{html_title(edge.get("contexts"))}</path>')
    labels = []
    for row in people:
        x0, y0 = people_pos[str(row.get("entity_id"))]
        labels.append(f'<circle cx="{x0}" cy="{y0}" r="6" fill="#2b6cb0"/><text x="{x0 - 12}" y="{y0 + 4}" class="mini-label" text-anchor="end">{html.escape(short_label(row.get("label"), 28))}</text>')
    for row in sources:
        x0, y0 = source_pos[str(row.get("source_id"))]
        labels.append(f'<circle cx="{x0}" cy="{y0}" r="5" fill="{color_for(row.get("reliability_grade"))}"/><text x="{x0 + 12}" y="{y0 + 4}" class="mini-label">{html.escape(short_label(row.get("label"), 36))}</text>')
    return (
        '<div class="chart-shell scroll-x">'
        f'<svg class="chart-svg" style="min-width:{width}px" viewBox="0 0 {width} {height}" role="img" aria-label="Person source bipartite graph">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        '<text x="250" y="30" class="axis-label" text-anchor="middle">people</text><text x="820" y="30" class="axis-label" text-anchor="middle">sources</text>'
        f'{"".join(paths)}{"".join(labels)}</svg></div>'
    )
