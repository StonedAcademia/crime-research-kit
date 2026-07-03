"""Matrix and quality SVG renderers for analysis chart exports."""

from __future__ import annotations

import html
import math
from typing import Any

from adapters.ops.evidence.reports.analysis.classifiers import status_score
from adapters.ops.evidence.reports.analysis.svg.base import (
    CHART_COLORS,
    color_for,
    html_title,
    pie_path,
    short_label,
    svg_no_data,
)
from adapters.ops.evidence.reports.weights import parse_float


def render_heatmap_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return svg_no_data()
    row_keys = sorted({str(row.get("claim_type") or "unknown") for row in rows})
    col_keys = sorted({str(row.get("status") or "unknown") for row in rows}, key=lambda status: -status_score(status))
    cell = 48
    left, top = 210, 58
    width = left + cell * len(col_keys) + 40
    height = top + cell * len(row_keys) + 50
    by_key = {(str(row.get("claim_type") or "unknown"), str(row.get("status") or "unknown")): row for row in rows}
    cells = []
    for r_idx, row_key in enumerate(row_keys):
        y = top + r_idx * cell
        cells.append(f'<text x="{left - 12}" y="{y + 29}" class="mini-label" text-anchor="end">{html.escape(short_label(row_key, 28))}</text>')
        for c_idx, col_key in enumerate(col_keys):
            x = left + c_idx * cell
            row = by_key.get((row_key, col_key), {})
            count = int(row.get("claim_count") or 0)
            confidence = parse_float(row.get("avg_confidence"), 0.0)
            opacity = 0.18 + 0.72 * confidence
            fill = color_for(col_key, c_idx)
            cells.append(
                f'<g><rect x="{x}" y="{y}" width="{cell - 4}" height="{cell - 4}" rx="5" fill="{fill}" fill-opacity="{opacity:.2f}" stroke="#fff"/>'
                f'<text x="{x + cell / 2 - 2:.1f}" y="{y + 28}" class="heat-label" text-anchor="middle">{count if count else ""}</text>'
                f'{html_title(f"{row_key} / {col_key}: {count} claims, avg confidence {confidence}")}</g>'
            )
    headers = "".join(
        f'<text x="{left + idx * cell + cell / 2 - 2:.1f}" y="42" class="mini-label" text-anchor="middle" transform="rotate(-35 {left + idx * cell + cell / 2 - 2:.1f} 42)">{html.escape(short_label(col, 16))}</text>'
        for idx, col in enumerate(col_keys)
    )
    return (
        '<div class="chart-shell scroll-x">'
        f'<svg class="chart-svg" style="min-width:{width}px" viewBox="0 0 {width} {height}" role="img" aria-label="Evidence confidence heatmap">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>{headers}{"".join(cells)}'
        "</svg></div>"
    )


def render_fragility_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return svg_no_data()
    width, height = 900, 360
    left, right, top, bottom = 68, 28, 40, 54
    max_load = max((parse_float(row.get("load_bearing_score"), 0.0) for row in rows), default=1.0) or 1.0
    points = []
    for idx, row in enumerate(rows[:42]):
        load = parse_float(row.get("load_bearing_score"), 0.0)
        frag = parse_float(row.get("fragility_score"), 0.0)
        x = left + (width - left - right) * load / max_load
        y = top + (height - top - bottom) * (1 - frag)
        points.append(
            f'<g><line x1="{x:.1f}" y1="{height - bottom}" x2="{x:.1f}" y2="{y:.1f}" stroke="#c8d4df" stroke-width="1"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{color_for(row.get("fragility_tier"), idx)}" fill-opacity="0.86">'
            f'{html_title(row.get("record_id"))}</circle></g>'
        )
    return (
        '<div class="chart-shell">'
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Bridge fragility scatterplot">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" class="axis"/>'
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" class="axis"/>'
        f'<text x="{width / 2}" y="{height - 14}" class="axis-label" text-anchor="middle">load-bearing bridge count</text>'
        f'<text x="18" y="{height / 2}" class="axis-label" text-anchor="middle" transform="rotate(-90 18 {height / 2})">fragility score</text>'
        f'{"".join(points)}</svg></div>'
    )


def render_claim_matrix_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return svg_no_data()
    claim_order = sorted({str(row.get("claim_id")) for row in rows})[:28]
    source_counts: dict[str, int] = {}
    for row in rows:
        sid = str(row.get("source_id"))
        source_counts[sid] = source_counts.get(sid, 0) + 1
    source_order = [sid for sid, _ in sorted(source_counts.items(), key=lambda item: (-item[1], item[0]))[:28]]
    cell = 20
    left, top = 190, 118
    width = left + cell * len(source_order) + 38
    height = top + cell * len(claim_order) + 45
    cells = []
    grade_by_cell = {(str(row.get("claim_id")), str(row.get("source_id"))): str(row.get("source_grade") or "") for row in rows}
    for r_idx, claim_id in enumerate(claim_order):
        y = top + r_idx * cell
        cells.append(f'<text x="{left - 10}" y="{y + 14}" class="mini-label" text-anchor="end">{html.escape(short_label(claim_id, 26))}</text>')
        for c_idx, source_id in enumerate(source_order):
            x = left + c_idx * cell
            grade = grade_by_cell.get((claim_id, source_id))
            fill = color_for(grade, c_idx) if grade else "#edf2f7"
            opacity = "0.9" if grade else "0.55"
            title = f"{claim_id} / {source_id} / {grade or 'no link'}"
            cells.append(f'<rect x="{x}" y="{y}" width="{cell - 3}" height="{cell - 3}" rx="2" fill="{fill}" fill-opacity="{opacity}">{html_title(title)}</rect>')
    headers = "".join(
        f'<text x="{left + idx * cell + 8}" y="{top - 8}" class="mini-label" text-anchor="start" transform="rotate(-55 {left + idx * cell + 8} {top - 8})">{html.escape(short_label(source_id, 12))}</text>'
        for idx, source_id in enumerate(source_order)
    )
    return (
        '<div class="chart-shell scroll-x">'
        f'<svg class="chart-svg" style="min-width:{width}px" viewBox="0 0 {width} {height}" role="img" aria-label="Claim source matrix">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>{headers}{"".join(cells)}'
        "</svg></div>"
    )


def render_source_quality_svg(grade_rows: list[dict[str, Any]], source_rows: list[dict[str, Any]]) -> str:
    if not grade_rows:
        return svg_no_data()
    width, height = 900, 360
    total = sum(int(row.get("count") or 0) for row in grade_rows) or 1
    start = -math.pi / 2
    slices = []
    legend = []
    for idx, row in enumerate(grade_rows):
        count = int(row.get("count") or 0)
        end = start + 2 * math.pi * count / total
        grade = str(row.get("grade") or "unknown")
        color = color_for(grade, idx)
        slices.append(f'<path d="{pie_path(190, 178, 116, start, end)}" fill="{color}" fill-opacity="0.82">{html_title(f"{grade}: {count}")}</path>')
        legend.append(f'<g><rect x="352" y="{84 + idx * 28}" width="16" height="16" rx="3" fill="{color}"/><text x="376" y="{97 + idx * 28}" class="node-label">Grade {html.escape(grade)}: {count}</text></g>')
        start = end
    footprints = []
    metric_keys = ["claim_count", "event_count", "event_link_count", "relationship_count", "person_count"]
    totals = {key: sum(int(row.get(key) or 0) for row in source_rows) for key in metric_keys}
    max_total = max(totals.values(), default=1) or 1
    for idx, key in enumerate(metric_keys):
        value = totals[key]
        x = 540 + idx * 62
        bar_height = 170 * value / max_total
        footprints.append(
            f'<g><rect x="{x}" y="{260 - bar_height:.1f}" width="34" height="{bar_height:.1f}" rx="4" fill="{CHART_COLORS[idx]}" fill-opacity="0.8"/>'
            f'<text x="{x + 17}" y="282" class="mini-label" text-anchor="middle" transform="rotate(-35 {x + 17} 282)">{html.escape(key.replace("_count", ""))}</text>'
            f'<text x="{x + 17}" y="{252 - bar_height:.1f}" class="heat-label" text-anchor="middle">{value}</text></g>'
        )
    return (
        '<div class="chart-shell">'
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Source quality dashboard">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        f'{"".join(slices)}<circle cx="190" cy="178" r="62" fill="#fff"/>'
        f'<text x="190" y="174" class="metric" text-anchor="middle">{total}</text><text x="190" y="196" class="mini-label" text-anchor="middle">sources</text>'
        f'{"".join(legend)}{"".join(footprints)}'
        '<text x="540" y="58" class="axis-label">Source coverage footprint</text>'
        "</svg></div>"
    )


def render_readiness_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return svg_no_data()
    width, height = 760, 320
    total = sum(int(row.get("count") or 0) for row in rows) or 1
    start = -math.pi / 2
    slices = []
    legend = []
    for idx, row in enumerate(rows):
        count = int(row.get("count") or 0)
        readiness = str(row.get("readiness") or "unknown")
        end = start + 2 * math.pi * count / total
        color = color_for(readiness, idx)
        slices.append(f'<path d="{pie_path(170, 160, 108, start, end)}" fill="{color}" fill-opacity="0.84">{html_title(f"{readiness}: {count}")}</path>')
        legend.append(f'<g><rect x="330" y="{58 + idx * 29}" width="17" height="17" rx="3" fill="{color}"/><text x="356" y="{72 + idx * 29}" class="node-label">{html.escape(readiness)} ({count})</text></g>')
        start = end
    return (
        '<div class="chart-shell">'
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Public narrative readiness donut">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        f'{"".join(slices)}<circle cx="170" cy="160" r="58" fill="#fff"/>'
        f'<text x="170" y="158" class="metric" text-anchor="middle">{total}</text><text x="170" y="180" class="mini-label" text-anchor="middle">records</text>'
        f'{"".join(legend)}</svg></div>'
    )
