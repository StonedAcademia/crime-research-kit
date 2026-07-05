"""Jinja report renderer: self-contained pages from typed models."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.render import _static_assets, render_dashboard, render_page, render_svg_doc, write_html
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.svg.network.bridges import build_sankey_figure
from crime_research_kit._runtime.core.models.reports import Dashboard, Rect, ReportPage, SvgDoc, TableBlock, Text

SVG_XMLNS = 'xmlns="http://www.w3.org/2000/svg"'
ROOT = Path(__file__).resolve().parents[4]
REPORT_BUILDERS = ROOT / "src" / "adapters" / "ops" / "evidence" / "reports"
FRONTEND_CSS = ROOT / "frontend" / "styles.css"
CSS_CLASS_ALLOWLIST: dict[str, str] = {}
CSS_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")


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
    html_without_allowed_uris = _strip_allowed_frontend_uris(html_text.replace(SVG_XMLNS, ""))
    assert html_text.startswith("<!doctype html>")
    assert "<style>" in html_text and "<script>" in html_text
    assert "http://" not in html_without_allowed_uris and "https://" not in html_without_allowed_uris


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
    html_without_allowed_uris = _strip_allowed_frontend_uris(html_text)
    assert html_text.startswith("<!doctype html>")
    assert "Demo Chart" in html_text and "demo.html" in html_text
    assert "Analysis charts: Case X" in html_text
    assert "http://" not in html_without_allowed_uris and "https://" not in html_without_allowed_uris


def test_write_html_replaces_target_atomically(tmp_path):
    target = tmp_path / "nested" / "page.html"
    write_html(target, "<!doctype html>first")
    write_html(target, "<!doctype html>second")
    assert target.read_text(encoding="utf-8") == "<!doctype html>second"
    assert not list(target.parent.glob("*.tmp"))


def test_sankey_node_boxes_are_styled_in_static_assets():
    figure = build_sankey_figure(
        nodes=[
            {"cluster_id": "C1", "cluster_label": "Origin cluster", "member_names": "Alice"},
            {"cluster_id": "C2", "cluster_label": "Target cluster", "member_names": "Bob"},
        ],
        links=[
            {
                "src_cluster": "C1",
                "dst_cluster": "C2",
                "public_readiness": "public_ready",
                "bridge_class": "personnel_bridge",
                "path": "C1 -> C2",
            }
        ],
    )
    svg_text = render_svg_doc(figure)
    css, _ = _static_assets()
    assert svg_text.count('class="node-box"') == 2
    assert re.search(r"\.node-box\{[^}]*\bfill:", css)


def test_report_builder_css_classes_are_styled():
    styles = FRONTEND_CSS.read_text(encoding="utf-8")
    emitted = _report_builder_css_classes()
    missing = sorted(
        token
        for token in emitted
        if token not in CSS_CLASS_ALLOWLIST and not re.search(rf"(?<![\w-])\.{re.escape(token)}(?![\w-])", styles)
    )
    assert not missing, "Unstyled report CSS classes: " + ", ".join(missing)


def _report_builder_css_classes() -> dict[str, Path]:
    classes: dict[str, Path] = {}
    for path in sorted(REPORT_BUILDERS.rglob("*.py")):
        for literal in _css_class_literals(path):
            for token in literal.split():
                if CSS_TOKEN.fullmatch(token):
                    classes.setdefault(token, path.relative_to(ROOT))
    return classes


def _css_class_literals(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    literals: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.keyword) or node.arg != "css_class":
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            literals.append(node.value.value)
        elif isinstance(node.value, ast.JoinedStr):
            literals.extend(part.value for part in node.value.values if isinstance(part, ast.Constant) and isinstance(part.value, str))
    return literals


def _strip_allowed_frontend_uris(text: str) -> str:
    pattern = r"https://tailwindcss\.com|http://www\.w3\.org/(?:1999/(?:xhtml|xlink)|2000/(?:svg|xmlns/)|XML/1998/namespace)"
    return re.sub(pattern, "", text)
