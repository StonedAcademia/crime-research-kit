"""Subcase timeline report page and SVG figure builders."""

from __future__ import annotations

from typing import Any

from core.models.reports import Circle, Line, ReportPage, SvgDoc, SvgElement, TableBlock, Text

from adapters.ops.evidence.ledger.records import flatten
from adapters.ops.evidence.ledger.scoring import date_sort_key
from adapters.ops.evidence.reports.analysis.pages.render import render_page
from adapters.ops.evidence.reports.common import truncate_label


def render_subcase_timeline_html(
    case_title: str,
    subcase_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    include_private: bool,
) -> str:
    return render_page(build_subcase_timeline_page(case_title, subcase_rows, event_rows, include_private))


def build_subcase_timeline_page(
    case_title: str,
    subcase_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    include_private: bool,
) -> ReportPage:
    return ReportPage(
        slug="subcase_timelines",
        title="Subcase timeline chart",
        case_title=case_title,
        summary=f"Scope: {'public and internal rows' if include_private else 'public-export rows only'}. Subcase lanes are inferred from source-bound event and claim text.",
        include_private=include_private,
        back_href="charts.md",
        back_label="Back to case charts index",
        figure=build_subcase_timeline_figure(subcase_rows, event_rows),
        tables=[TableBlock(title="Timeline rows", columns=["date", "subcase", "event", "status", "evidence", "sources", "claims"], rows=_table_rows(event_rows), limit=max(1, len(event_rows)))],
    )


def build_subcase_timeline_figure(subcase_rows: list[dict[str, Any]], event_rows: list[dict[str, Any]]) -> SvgDoc:
    width = 1320
    left = 260
    right = 40
    top = 70
    lane_h = 95
    height = max(360, top + lane_h * max(1, len(subcase_rows)) + 80)
    dated = [row for row in event_rows if date_sort_key(row.get("start_date"))[0] != 9999]
    years = [date_sort_key(row.get("start_date"))[0] for row in dated] or [2000]
    min_year = min(years)
    max_year = max(years) + 1
    span = max_year - min_year
    lane_y = {row["subcase_id"]: top + idx * lane_h for idx, row in enumerate(subcase_rows)}
    elements = [*_axis(width, right, top, height, left, min_year, max_year, span), *_lanes(subcase_rows, lane_y, left, width, right), *_points(event_rows, lane_y, left, width, right, min_year, span)]
    return SvgDoc(width=width, height=height, view_box=f"0 0 {width} {height}", role="img", aria_label="Subcase timeline chart", elements=elements)


def _axis(width: int, right: int, top: int, height: int, left: int, min_year: int, max_year: int, span: int) -> list[SvgElement]:
    axis: list[SvgElement] = [Line(x1=left, y1=top - 30, x2=width - right, y2=top - 30, css_class="axis")]
    for year in range(min_year, max_year + 1, max(1, (max_year - min_year) // 6 or 1)):
        x = left + ((year - min_year) / span) * (width - left - right)
        axis.append(Line(x1=round(x, 1), y1=top - 38, x2=round(x, 1), y2=height - 45, css_class="grid"))
        axis.append(Text(x=round(x, 1), y=top - 45, content=str(year), css_class="axis-label", anchor="middle"))
    return axis


def _lanes(subcase_rows: list[dict[str, Any]], lane_y: dict[str, int], left: int, width: int, right: int) -> list[SvgElement]:
    lanes: list[SvgElement] = []
    for row in subcase_rows:
        y = lane_y[row["subcase_id"]]
        lanes.append(Text(x=24, y=y + 6, content=row["subcase_title"], css_class="lane-label"))
        lanes.append(Line(x1=left, y1=y, x2=width - right, y2=y, css_class="lane"))
    return lanes


def _points(event_rows: list[dict[str, Any]], lane_y: dict[str, int], left: int, width: int, right: int, min_year: int, span: int) -> list[SvgElement]:
    points: list[SvgElement] = []
    for row in event_rows:
        subcase_id = row["subcase_id"]
        if subcase_id not in lane_y:
            continue
        year, month, day, _ = date_sort_key(row.get("start_date"))
        frac = (year - min_year) + ((month - 1) / 12) + ((day - 1) / 365)
        x = left + (frac / span) * (width - left - right)
        y = lane_y[subcase_id]
        color_class = "verified" if row.get("status") == "verified" else "single"
        points.extend([
            Circle(cx=round(x, 1), cy=round(y, 1), r=8, css_class=f"point {color_class}"),
            Text(x=round(x + 10, 1), y=round(y - 10, 1), content=truncate_label(str(row.get("title", "")), 38), css_class="event-label"),
            Text(x=round(x + 10, 1), y=round(y + 8, 1), content=str(row.get("start_date", "")), css_class="event-date"),
        ])
    return points


def _table_rows(event_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [{"date": str(row.get("start_date", "")), "subcase": str(row.get("subcase_title", "")), "event": str(row.get("title", "")), "status": str(row.get("status", "")), "evidence": flatten(row.get("evidence_levels")), "sources": str(row.get("source_grades", "")), "claims": flatten(row.get("claim_ids"))} for row in event_rows]
