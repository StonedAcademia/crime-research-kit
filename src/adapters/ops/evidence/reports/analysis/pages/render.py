"""HTML rendering helpers for analysis chart pages."""

from __future__ import annotations

import datetime as dt
import html
import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import jinja2

from adapters.ops.evidence.reports.analysis.pages.assets import analysis_chart_css, analysis_chart_files
from adapters.ops.evidence.reports.analysis.pages.interactions import analysis_chart_script
from adapters.ops.evidence.reports.analysis.svg.base import short_label
from adapters.ops.evidence.reports.common import parse_cell_list
from adapters.ops.evidence.ledger.records import flatten
from core.models.reports import Dashboard, ReportPage


@lru_cache(maxsize=1)
def _environment() -> jinja2.Environment:
    package_dir = Path(__file__).resolve().parent / "templates_data"
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(package_dir)),
        autoescape=jinja2.select_autoescape(["html", "j2"]),
        undefined=jinja2.StrictUndefined,
    )


@lru_cache(maxsize=1)
def _static_assets() -> tuple[str, str]:
    static = Path(__file__).resolve().parent / "templates_data" / "static"
    css = static.joinpath("app.css").read_text(encoding="utf-8")
    if css.startswith("/*! tailwindcss"):
        css = "\n".join(css.splitlines()[1:])
    js = static.joinpath("app.js").read_text(encoding="utf-8")
    return css, js


def render_page(page: ReportPage) -> str:
    css, js = _static_assets()
    return _environment().get_template("layouts/page.html.j2").render(page=page, app_css=css, app_js=js)


def render_dashboard(dash: Dashboard) -> str:
    css, js = _static_assets()
    return _environment().get_template("layouts/dashboard.html.j2").render(dash=dash, app_css=css, app_js=js)


def write_html(path: Path, html_text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(html_text)
    os.replace(tmp, path)


def chart_row_table(rows: list[dict[str, Any]], columns: list[str], limit: int = 25) -> str:
    display_rows = rows[:limit]
    if not display_rows:
        return "<p class=\"muted\">No rows.</p>"
    head = "".join(f"<th>{html.escape(col.replace('_', ' ').title())}</th>" for col in columns)
    body = []
    for row in display_rows:
        cells = "".join(f"<td>{html.escape(flatten(row.get(col)))}</td>" for col in columns)
        body.append(f"<tr>{cells}</tr>")
    extra = f"<p class=\"muted\">Showing {len(display_rows)} of {len(rows)} rows.</p>" if len(rows) > limit else ""
    return f"<div class=\"table-wrap\"><table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>{extra}"


def filter_terms(rows: list[dict[str, Any]], keys: list[str], limit: int = 10) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in keys:
            values = parse_cell_list(row.get(key)) or [str(row.get(key, ""))]
            for value in values:
                text = str(value).strip()
                if not text or text in seen or len(text) > 48:
                    continue
                seen.add(text)
                terms.append(text)
                if len(terms) >= limit:
                    return terms
    return terms


def render_analysis_chart_page(case_title: str, include_private: bool, spec: dict[str, Any]) -> str:
    generated = dt.datetime.now(dt.timezone.utc).isoformat()
    filter_buttons = "".join(
        f'<button type="button" data-query="{html.escape(term)}" aria-pressed="false">{html.escape(short_label(term, 22))}</button>'
        for term in spec.get("filters", [])
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(spec["title"])} - {html.escape(case_title)}</title>
{analysis_chart_css()}
</head>
<body>
<header>
<p><a class="back-link" href="analysis_charts.html">Back to chart index</a></p>
<h1>{int(spec["number"])}. {html.escape(spec["title"])}</h1>
<p>{html.escape(spec["description"])}</p>
<p>Generated {html.escape(generated)}. Scope: {'public and private/internal rows' if include_private else 'public-export rows only'}.</p>
<p>CSV source: <code>{html.escape(spec["csvs"])}</code></p>
</header>
<main>
<section>
<div class="toolbar">
<input type="search" data-search placeholder="Filter visible marks by label, status, source, claim, or path">
{filter_buttons}
<button type="button" data-query="" aria-pressed="false">All</button>
<button type="button" data-reset>Reset selection</button>
</div>
<div class="chart-layout">
<div>
{spec["chart_html"]}
<details class="data-preview"><summary>Data preview</summary>{spec["preview_html"]}</details>
</div>
<aside class="inspector" data-inspector>
<p class="inspector-title">Inspector</p>
<div class="inspector-body" data-inspector-body></div>
</aside>
</div>
</section>
</main>
{analysis_chart_script()}
</body>
</html>
"""


def render_analysis_dashboard(case_title: str, include_private: bool, chart_specs: list[dict[str, Any]]) -> str:
    generated = dt.datetime.now(dt.timezone.utc).isoformat()
    file_rows = "".join(
        f"<li><code>{html.escape(name)}</code> - {html.escape(path)}</li>"
        for name, path in analysis_chart_files()
    )
    cards = "".join(
        '<article class="card">'
        f'<h2>{int(spec["number"])}. {html.escape(spec["title"])}</h2>'
        f'<p>{html.escape(spec["description"])}</p>'
        f'<p class="muted"><code>{html.escape(spec["csvs"])}</code></p>'
        f'<a class="card-link" href="{html.escape(spec["filename"])}">Open interactive chart</a>'
        "</article>"
        for spec in chart_specs
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Analysis chart index - {html.escape(case_title)}</title>
{analysis_chart_css()}
</head>
<body>
<header>
<h1>Analysis charts: {html.escape(case_title)}</h1>
<p>Generated {html.escape(generated)}. Scope: {'public and private/internal rows' if include_private else 'public-export rows only'}.</p>
<p>Open each chart in its own page for data-derived filters, hover/click inspection, keyboard focus, and collapsible table previews.</p>
</header>
<main>
<section class="wide"><h2>Files</h2><ul>{file_rows}</ul></section>
<div class="grid">{cards}</div>
</main>
</body>
</html>
"""
