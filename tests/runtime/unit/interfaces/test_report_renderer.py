"""Jinja report renderer: self-contained pages from typed models."""

from __future__ import annotations

import ast
import importlib.util
import json
import re
from pathlib import Path

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.render import _static_assets, render_dashboard, render_page, render_svg_doc, write_html
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.svg.network.bridges import build_sankey_figure
from crime_research_kit._runtime.core.models.reports import Dashboard, Rect, ReportPage, SvgDoc, TableBlock, Text

SVG_XMLNS = 'xmlns="http://www.w3.org/2000/svg"'
ROOT = Path(__file__).resolve().parents[4]
REPORT_BUILDERS = ROOT / "src" / "adapters" / "ops" / "evidence" / "reports"
FRONTEND_CSS = ROOT / "frontend" / "styles.css"
SLIDE_DECK_SCRIPT = ROOT / "deployment" / "scripts" / "tools" / "slides" / "build_case_slide_deck.py"
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


def test_case_slide_deck_embeds_generated_chart_payloads(tmp_path):
    module = _load_slide_deck_module()
    case_dir = tmp_path / "case"
    _write_case_fixture(case_dir)
    html_text = module.render(module.slide_data(case_dir))

    assert len(module.slide_data(case_dir)["charts"]) == 4
    assert "Internal review deck" in html_text
    assert "data-chart-index" in html_text
    assert "First Chart" in html_text
    assert "href=" not in html_text


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


def _load_slide_deck_module():
    spec = importlib.util.spec_from_file_location("build_case_slide_deck", SLIDE_DECK_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _write_case_fixture(case_dir: Path) -> None:
    _write_json(case_dir / "case.json", {"title": "Demo Case"})
    for name in ["sources", "entities", "claims", "events", "relationships", "source_spans"]:
        _write_jsonl(case_dir / "records" / f"{name}.jsonl", [{"status": "verified"}])
    for file_name, count_key in [
        ("public_export_audit.json", "issue_count"),
        ("privacy_redaction_audit.json", "issue_count"),
        ("narrative_readiness_review.json", "issue_count"),
        ("source_independence_report.json", "flag_count"),
        ("claim_contradiction_audit.json", "flag_count"),
    ]:
        _write_json(case_dir / "exports" / file_name, {count_key: 1, "summary": {"blocker": 1}})
    analysis = case_dir / "exports/internal/analysis_charts"
    charts = case_dir / "exports/internal/charts"
    analysis.mkdir(parents=True)
    charts.mkdir(parents=True)
    for path, title in {
        analysis / "analysis_charts.html": "Dashboard",
        analysis / "01_first_chart.html": "First Chart",
        charts / "people_graph.html": "People Graph",
        charts / "subcase_timelines.html": "Timelines",
    }.items():
        path.write_text(f"<!doctype html><title>{title}</title>", encoding="utf-8")
    (analysis / "source_quality_dashboard.csv").write_text("source_id,grade,title,publisher\nS1,A,One,Pub\n", encoding="utf-8")
    (analysis / "public_narrative_readiness.csv").write_text("claim_id,status,public_export,privacy_review\nC1,verified,true,clear\n", encoding="utf-8")
    (case_dir / "exports/evidence_board.md").write_text("# Evidence\n\n| ID | Value |\n|---|---|\n| A | B |\n", encoding="utf-8")


def _strip_allowed_frontend_uris(text: str) -> str:
    pattern = r"https://tailwindcss\.com|http://www\.w3\.org/(?:1999/(?:xhtml|xlink)|2000/(?:svg|xmlns/)|XML/1998/namespace)"
    return re.sub(pattern, "", text)
