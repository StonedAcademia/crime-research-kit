"""HTML rendering helpers for analysis chart pages."""

from __future__ import annotations

import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import jinja2

from adapters.ops.evidence.reports.common import parse_cell_list
from core.models.reports import Dashboard, ReportPage, SvgDoc


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


def render_svg_doc(doc: SvgDoc) -> str:
    return str(_environment().get_template("figures/svg.j2").module.svg(doc))


def write_html(path: Path, html_text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(html_text)
    os.replace(tmp, path)


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
