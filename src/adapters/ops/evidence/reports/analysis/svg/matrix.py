"""Matrix and quality SVG figure builders for analysis chart exports."""

from __future__ import annotations

import math
from typing import Any

from core.models.reports import Circle, Group, Line, Path, Rect, SvgDoc, SvgElement, Text

from adapters.ops.evidence.ledger.records import flatten
from adapters.ops.evidence.reports.analysis.classifiers import status_score
from adapters.ops.evidence.reports.analysis.pages.render import render_svg_doc
from adapters.ops.evidence.reports.analysis.svg.base import CHART_COLORS, color_for, pie_path, short_label
from adapters.ops.evidence.reports.weights import parse_float


def _chart_doc(width: int, height: int, label: str, elements: list[SvgElement], style: str = "") -> SvgDoc:
    return SvgDoc(
        width=width, height=height, view_box=f"0 0 {width} {height}", css_class="chart-svg", style=style, role="img", aria_label=label,
        elements=[Rect(x=0, y=0, width=width, height=height, rx=8, css_class="chart-bg"), *elements],
    )


def _no_data_figure() -> SvgDoc:
    text = Text(x=450, y=112, content="No chart data", css_class="axis-label", anchor="middle")
    return _chart_doc(900, 220, "No chart data", [text])


def build_heatmap_figure(rows: list[dict[str, Any]]) -> SvgDoc:
    if not rows:
        return _no_data_figure()
    row_keys = sorted({str(row.get("claim_type") or "unknown") for row in rows})
    col_keys = sorted({str(row.get("status") or "unknown") for row in rows}, key=lambda status: -status_score(status))
    cell = 48
    left, top = 210, 58
    width = left + cell * len(col_keys) + 40
    height = top + cell * len(row_keys) + 50
    by_key = {(str(row.get("claim_type") or "unknown"), str(row.get("status") or "unknown")): row for row in rows}
    elements: list[SvgElement] = []
    for idx, col in enumerate(col_keys):
        x = left + idx * cell + cell / 2 - 2
        elements.append(Text(x=x, y=42, content=short_label(col, 16), css_class="mini-label", anchor="middle", transform=f"rotate(-35 {x:.1f} 42)"))
    for r_idx, row_key in enumerate(row_keys):
        y = top + r_idx * cell
        elements.append(Text(x=left - 12, y=y + 29, content=short_label(row_key, 28), css_class="mini-label", anchor="end"))
        for c_idx, col_key in enumerate(col_keys):
            x = left + c_idx * cell
            row = by_key.get((row_key, col_key), {})
            count = int(row.get("claim_count") or 0)
            confidence = parse_float(row.get("avg_confidence"), 0.0)
            fill = color_for(col_key, c_idx)
            rect = Rect(
                x=x, y=y, width=cell - 4, height=cell - 4, rx=5, fill=fill, fill_opacity=f"{0.18 + 0.72 * confidence:.2f}",
                stroke="#fff", title=f"{row_key} / {col_key}: {count} claims, avg confidence {confidence}",
            )
            text = Text(x=x + cell / 2 - 2, y=y + 28, content=str(count) if count else "", css_class="heat-label", anchor="middle")
            elements.append(Group(children=[rect, text]))
    return _chart_doc(width, height, "Evidence confidence heatmap", elements, style=f"min-width:{width}px")


def render_heatmap_svg(rows: list[dict[str, Any]]) -> str:
    return render_svg_doc(build_heatmap_figure(rows))


def build_fragility_figure(rows: list[dict[str, Any]]) -> SvgDoc:
    if not rows:
        return _no_data_figure()
    width, height = 900, 360
    left, right, top, bottom = 68, 28, 40, 54
    max_load = max((parse_float(row.get("load_bearing_score"), 0.0) for row in rows), default=1.0) or 1.0
    elements: list[SvgElement] = [
        Line(x1=left, y1=height - bottom, x2=width - right, y2=height - bottom, css_class="axis"),
        Line(x1=left, y1=top, x2=left, y2=height - bottom, css_class="axis"),
        Text(x=width / 2, y=height - 14, content="load-bearing bridge count", css_class="axis-label", anchor="middle"),
        Text(x=18, y=height / 2, content="fragility score", css_class="axis-label", anchor="middle", transform=f"rotate(-90 18 {height / 2})"),
    ]
    for idx, row in enumerate(rows[:42]):
        load = parse_float(row.get("load_bearing_score"), 0.0)
        frag = parse_float(row.get("fragility_score"), 0.0)
        x = left + (width - left - right) * load / max_load
        y = top + (height - top - bottom) * (1 - frag)
        line = Line(x1=round(x, 1), y1=height - bottom, x2=round(x, 1), y2=round(y, 1), stroke="#c8d4df")
        point = Circle(cx=round(x, 1), cy=round(y, 1), r=7, fill=color_for(row.get("fragility_tier"), idx), fill_opacity="0.86", title=flatten(row.get("record_id")))
        elements.append(Group(children=[line, point]))
    return _chart_doc(width, height, "Bridge fragility scatterplot", elements)


def render_fragility_svg(rows: list[dict[str, Any]]) -> str:
    return render_svg_doc(build_fragility_figure(rows))


def build_claim_matrix_figure(rows: list[dict[str, Any]]) -> SvgDoc:
    if not rows:
        return _no_data_figure()
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
    grade_by_cell = {(str(row.get("claim_id")), str(row.get("source_id"))): str(row.get("source_grade") or "") for row in rows}
    elements: list[SvgElement] = []
    for idx, source_id in enumerate(source_order):
        x = left + idx * cell + 8
        y = top - 8
        elements.append(Text(x=x, y=y, content=short_label(source_id, 12), css_class="mini-label", transform=f"rotate(-55 {x} {y})"))
    for r_idx, claim_id in enumerate(claim_order):
        y = top + r_idx * cell
        elements.append(Text(x=left - 10, y=y + 14, content=short_label(claim_id, 26), css_class="mini-label", anchor="end"))
        for c_idx, source_id in enumerate(source_order):
            x = left + c_idx * cell
            grade = grade_by_cell.get((claim_id, source_id))
            fill = color_for(grade, c_idx) if grade else "#edf2f7"
            title = f"{claim_id} / {source_id} / {grade or 'no link'}"
            elements.append(Rect(x=x, y=y, width=cell - 3, height=cell - 3, rx=2, fill=fill, fill_opacity="0.9" if grade else "0.55", title=title))
    return _chart_doc(width, height, "Claim source matrix", elements, style=f"min-width:{width}px")


def render_claim_matrix_svg(rows: list[dict[str, Any]]) -> str:
    return render_svg_doc(build_claim_matrix_figure(rows))


def build_source_quality_figure(grade_rows: list[dict[str, Any]], source_rows: list[dict[str, Any]]) -> SvgDoc:
    if not grade_rows:
        return _no_data_figure()
    width, height = 900, 360
    total = sum(int(row.get("count") or 0) for row in grade_rows) or 1
    start = -math.pi / 2
    elements: list[SvgElement] = []
    for idx, row in enumerate(grade_rows):
        count = int(row.get("count") or 0)
        end = start + 2 * math.pi * count / total
        grade = str(row.get("grade") or "unknown")
        color = color_for(grade, idx)
        path = Path(d=pie_path(190, 178, 116, start, end), fill=color, fill_opacity="0.82", title=f"{grade}: {count}")
        legend = Group(children=[Rect(x=352, y=84 + idx * 28, width=16, height=16, rx=3, fill=color), Text(x=376, y=97 + idx * 28, content=f"Grade {grade}: {count}", css_class="node-label")])
        elements.extend([path, legend])
        start = end
    elements.extend([Circle(cx=190, cy=178, r=62, fill="#fff"), Text(x=190, y=174, content=str(total), css_class="metric", anchor="middle"), Text(x=190, y=196, content="sources", css_class="mini-label", anchor="middle")])
    metric_keys = ["claim_count", "event_count", "event_link_count", "relationship_count", "person_count"]
    totals = {key: sum(int(row.get(key) or 0) for row in source_rows) for key in metric_keys}
    max_total = max(totals.values(), default=1) or 1
    for idx, key in enumerate(metric_keys):
        value = totals[key]
        x = 540 + idx * 62
        bar_height = 170 * value / max_total
        label_x = x + 17
        bar = Rect(x=x, y=round(260 - bar_height, 1), width=34, height=round(bar_height, 1), rx=4, fill=CHART_COLORS[idx], fill_opacity="0.8")
        label = Text(x=label_x, y=282, content=key.replace("_count", ""), css_class="mini-label", anchor="middle", transform=f"rotate(-35 {label_x} 282)")
        value_label = Text(x=label_x, y=round(252 - bar_height, 1), content=str(value), css_class="heat-label", anchor="middle")
        elements.append(Group(children=[bar, label, value_label]))
    elements.append(Text(x=540, y=58, content="Source coverage footprint", css_class="axis-label"))
    return _chart_doc(width, height, "Source quality dashboard", elements)


def render_source_quality_svg(grade_rows: list[dict[str, Any]], source_rows: list[dict[str, Any]]) -> str:
    return render_svg_doc(build_source_quality_figure(grade_rows, source_rows))


def build_readiness_figure(rows: list[dict[str, Any]]) -> SvgDoc:
    if not rows:
        return _no_data_figure()
    width, height = 760, 320
    total = sum(int(row.get("count") or 0) for row in rows) or 1
    start = -math.pi / 2
    elements: list[SvgElement] = []
    for idx, row in enumerate(rows):
        count = int(row.get("count") or 0)
        readiness = str(row.get("readiness") or "unknown")
        end = start + 2 * math.pi * count / total
        color = color_for(readiness, idx)
        path = Path(d=pie_path(170, 160, 108, start, end), fill=color, fill_opacity="0.84", title=f"{readiness}: {count}")
        legend = Group(children=[Rect(x=330, y=58 + idx * 29, width=17, height=17, rx=3, fill=color), Text(x=356, y=72 + idx * 29, content=f"{readiness} ({count})", css_class="node-label")])
        elements.extend([path, legend])
        start = end
    elements.extend([Circle(cx=170, cy=160, r=58, fill="#fff"), Text(x=170, y=158, content=str(total), css_class="metric", anchor="middle"), Text(x=170, y=180, content="records", css_class="mini-label", anchor="middle")])
    return _chart_doc(width, height, "Public narrative readiness donut", elements)


def render_readiness_svg(rows: list[dict[str, Any]]) -> str:
    return render_svg_doc(build_readiness_figure(rows))
