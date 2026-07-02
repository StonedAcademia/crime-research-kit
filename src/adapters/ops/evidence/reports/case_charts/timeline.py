"""Subcase timeline HTML renderer."""

from __future__ import annotations

import html
from typing import Any

from adapters.ops.evidence.reports.common import truncate_label
from adapters.ops.evidence.shared.records import flatten
from adapters.ops.evidence.shared.scoring import date_sort_key


def render_subcase_timeline_html(
    case_title: str,
    subcase_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    include_private: bool,
) -> str:
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
    axis = _axis(width, right, top, height, left, min_year, max_year, span)
    lanes = _lanes(subcase_rows, lane_y, left, width, right)
    points = _points(event_rows, lane_y, left, width, right, min_year, span)
    table_rows = _table_rows(event_rows)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Subcase timeline chart - {html.escape(case_title)}</title>
<style>
body {{ margin: 0; font-family: Arial, sans-serif; color: #1f2933; background: #f7f8fa; }}
main {{ max-width: 1440px; margin: 0 auto; padding: 28px; }}
h1 {{ font-size: 26px; margin: 0 0 6px; }}
p {{ max-width: 980px; line-height: 1.45; }}
.panel {{ background: #fff; border: 1px solid #d8dee6; border-radius: 8px; padding: 18px; margin-top: 18px; }}
svg {{ width: 100%; height: auto; background: #fbfcfe; border: 1px solid #d8dee6; border-radius: 8px; }}
.axis {{ stroke: #334155; stroke-width: 1.5; }}
.grid {{ stroke: #d8dee6; stroke-width: 1; }}
.lane {{ stroke: #cbd5e1; stroke-width: 1.5; }}
.lane-label {{ fill: #111827; font-size: 13px; font-weight: 700; }}
.axis-label {{ fill: #475569; font-size: 12px; text-anchor: middle; }}
.point {{ stroke: #ffffff; stroke-width: 2; }}
.verified {{ fill: #2563eb; }}
.single {{ fill: #0f766e; }}
.event-label {{ fill: #111827; font-size: 12px; font-weight: 700; paint-order: stroke; stroke: #fbfcfe; stroke-width: 4px; }}
.event-date {{ fill: #475569; font-size: 11px; paint-order: stroke; stroke: #fbfcfe; stroke-width: 4px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ border-bottom: 1px solid #e2e8f0; padding: 8px; text-align: left; vertical-align: top; }}
th {{ background: #eef2f7; }}
</style>
</head>
<body>
<main>
<h1>Subcase timeline chart</h1>
<p>{html.escape(case_title)}. Scope: {"public and internal rows" if include_private else "public-export rows only"}. Subcase lanes are inferred from source-bound event and claim text.</p>
<section class="panel">
<svg viewBox="0 0 {width} {height}" role="img" aria-label="Subcase timeline chart">
{''.join(axis)}
{''.join(lanes)}
{''.join(points)}
</svg>
</section>
<section class="panel">
<h2>Timeline rows</h2>
<table>
<thead><tr><th>Date</th><th>Subcase</th><th>Event</th><th>Status</th><th>Evidence</th><th>Sources</th><th>Claims</th></tr></thead>
<tbody>
{table_rows}
</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def _axis(width: int, right: int, top: int, height: int, left: int, min_year: int, max_year: int, span: int) -> list[str]:
    axis = [f'<line x1="{left}" y1="{top - 30}" x2="{width - right}" y2="{top - 30}" class="axis" />']
    for year in range(min_year, max_year + 1, max(1, (max_year - min_year) // 6 or 1)):
        x = left + ((year - min_year) / span) * (width - left - right)
        axis.append(f'<line x1="{x:.1f}" y1="{top - 38}" x2="{x:.1f}" y2="{height - 45}" class="grid" />')
        axis.append(f'<text x="{x:.1f}" y="{top - 45}" class="axis-label">{year}</text>')
    return axis


def _lanes(subcase_rows: list[dict[str, Any]], lane_y: dict[str, int], left: int, width: int, right: int) -> list[str]:
    lanes = []
    for row in subcase_rows:
        y = lane_y[row["subcase_id"]]
        lanes.append(f'<text x="24" y="{y + 6}" class="lane-label">{html.escape(row["subcase_title"])}</text>')
        lanes.append(f'<line x1="{left}" y1="{y}" x2="{width - right}" y2="{y}" class="lane" />')
    return lanes


def _points(event_rows: list[dict[str, Any]], lane_y: dict[str, int], left: int, width: int, right: int, min_year: int, span: int) -> list[str]:
    points = []
    for row in event_rows:
        subcase_id = row["subcase_id"]
        if subcase_id not in lane_y:
            continue
        year, month, day, _ = date_sort_key(row.get("start_date"))
        frac = (year - min_year) + ((month - 1) / 12) + ((day - 1) / 365)
        x = left + (frac / span) * (width - left - right)
        y = lane_y[subcase_id]
        color_class = "verified" if row.get("status") == "verified" else "single"
        label = truncate_label(str(row.get("title", "")), 38)
        points.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" class="point {color_class}" />')
        points.append(f'<text x="{x + 10:.1f}" y="{y - 10:.1f}" class="event-label">{html.escape(label)}</text>')
        points.append(f'<text x="{x + 10:.1f}" y="{y + 8:.1f}" class="event-date">{html.escape(str(row.get("start_date", "")))}</text>')
    return points


def _table_rows(event_rows: list[dict[str, Any]]) -> str:
    return "\n".join("<tr>" f"<td>{html.escape(str(row.get('start_date', '')))}</td>" f"<td>{html.escape(str(row.get('subcase_title', '')))}</td>" f"<td>{html.escape(str(row.get('title', '')))}</td>" f"<td>{html.escape(str(row.get('status', '')))}</td>" f"<td>{html.escape(flatten(row.get('evidence_levels')))}</td>" f"<td>{html.escape(str(row.get('source_grades', '')))}</td>" f"<td>{html.escape(flatten(row.get('claim_ids')))}</td>" "</tr>" for row in event_rows)
