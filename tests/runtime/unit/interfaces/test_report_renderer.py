"""Jinja report renderer: self-contained pages from typed models."""

from __future__ import annotations

from core.models.reports import Dashboard, Rect, ReportPage, SvgDoc, TableBlock, Text
from adapters.ops.evidence.reports.analysis.pages.render import render_dashboard, render_page, write_html

SVG_XMLNS = 'xmlns="http://www.w3.org/2000/svg"'


def _page() -> ReportPage:
    return ReportPage(
        slug="demo",
        title="Demo Chart",
        case_title="Case X",
        filters=["alpha", "beta"],
        figure=SvgDoc(
            width=100,
            height=40,
            elements=[
                Rect(x=1, y=2, width=10, height=5, css_class="node", data={"query": "alpha"}),
                Text(x=5, y=30, content="Alpha & Co", anchor="middle"),
            ],
        ),
        table=TableBlock(columns=["name", "status"], rows=[{"name": "A", "status": "verified"}]),
    )


def test_render_page_is_self_contained_html():
    html_text = render_page(_page())
    html_without_xmlns = html_text.replace(SVG_XMLNS, "")
    assert html_text.startswith("<!doctype html>")
    assert "<style>" in html_text and "<script>" in html_text
    assert "http://" not in html_without_xmlns and "https://" not in html_without_xmlns


def test_render_page_escapes_and_carries_data_attrs():
    html_text = render_page(_page())
    assert "Alpha &amp; Co" in html_text
    assert 'data-query="alpha"' in html_text
    assert '<rect x="1.0" y="2.0"' in html_text or '<rect x="1" y="2"' in html_text


def test_render_page_renders_table_and_filters():
    html_text = render_page(_page())
    assert "<table" in html_text and "verified" in html_text
    assert html_text.count("crk-filter-btn") >= 2


def test_render_dashboard_links_pages_and_summaries():
    dash = Dashboard(case_title="Case X", pages=[_page()])
    html_text = render_dashboard(dash)
    assert html_text.startswith("<!doctype html>")
    assert "Demo Chart" in html_text and "demo.html" in html_text
    assert "Analysis charts: Case X" in html_text
    assert "http://" not in html_text and "https://" not in html_text


def test_write_html_replaces_target_atomically(tmp_path):
    target = tmp_path / "nested" / "page.html"
    write_html(target, "<!doctype html>first")
    write_html(target, "<!doctype html>second")
    assert target.read_text(encoding="utf-8") == "<!doctype html>second"
    assert not list(target.parent.glob("*.tmp"))
