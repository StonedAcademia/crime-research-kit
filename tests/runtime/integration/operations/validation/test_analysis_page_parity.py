"""New analysis page models preserve legacy page content signatures."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from adapters.ops.evidence.reports.analysis.command.builders.bridges import build_cluster_bridges
from adapters.ops.evidence.reports.analysis.command.builders.evidence import build_evidence_products
from adapters.ops.evidence.reports.analysis.command.builders.facets.boundary import (
    build_boundary_rows,
    build_readiness_products,
)
from adapters.ops.evidence.reports.analysis.command.builders.facets.people import (
    build_fragility,
    build_person_source_products,
)
from adapters.ops.evidence.reports.analysis.command.builders.facets.relationships import (
    build_relation_type_counts,
)
from adapters.ops.evidence.reports.analysis.command.builders.facets.timelines import build_swimlanes
from adapters.ops.evidence.reports.analysis.command.builders.layered import build_layered_graphs
from adapters.ops.evidence.reports.analysis.command.builders.paths import build_path_atlas
from adapters.ops.evidence.reports.analysis.command.context import load_analysis_context
from adapters.ops.evidence.reports.analysis.command.output import _chart_data
from adapters.ops.evidence.reports.analysis.pages.render import render_page, render_svg_doc
from adapters.ops.evidence.reports.analysis.pages.specs import build_analysis_chart_specs
from adapters.ops.evidence.reports.case_charts.command import export_case_charts
from adapters.ops.evidence.reports.clusters.command import export_people_clusters


ROOT = Path(__file__).resolve().parents[5]
SYNTHETIC_CASE = ROOT / "data" / "examples" / "synthetic_case"
FIXTURE = Path(__file__).with_name("analysis_page_signatures.json")
SECTION_KEYS = {"case_charts_figures", "case_charts_pages", "clusters_figures", "clusters_pages", "figures"}


def _signature(html_text: str) -> dict[str, Any]:
    title_match = re.search(r"<title>(.*?)</title>", html_text)
    if not title_match:
        raise AssertionError("rendered page did not include a <title>")
    return {
        "title": title_match.group(1),
        "row_count": html_text.count("<tr"),
        "filter_terms": sorted(set(re.findall(r'data-query="([^"]+)"', html_text))),
        "svg_count": html_text.count("<svg"),
    }


def svg_signature(svg_text: str) -> dict:
    root = ET.fromstring(svg_text)
    ns = "{http://www.w3.org/2000/svg}"
    if root.tag.replace(ns, "") != "svg":
        for el in root.iter():
            if el.tag.replace(ns, "") == "svg":
                root = el
                break
    counts: dict[str, int] = {}
    labels: list[str] = []
    for el in root.iter():
        tag = el.tag.replace(ns, "")
        key = f"{tag}.{el.get('class') or ''}"
        counts[key] = counts.get(key, 0) + 1
        if tag == "text" and (el.text or "").strip():
            labels.append(el.text.strip())
    return {"counts": dict(sorted(counts.items())), "labels": sorted(labels)}


def _first_svg(html_text: str) -> str:
    match = re.search(r"<svg\b.*?</svg>", html_text, flags=re.S)
    if not match:
        raise AssertionError("rendered page did not include an <svg>")
    svg = match.group(0)
    return svg if "xmlns=" in svg.split(">", 1)[0] else svg.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)


def _build_products(ctx: Any) -> dict[str, Any]:
    products: dict[str, Any] = {}
    products.update(build_cluster_bridges(ctx))
    products.update(build_path_atlas(ctx))
    products.update(build_layered_graphs(ctx))
    products.update(build_evidence_products(ctx))
    products["boundary_rows"] = build_boundary_rows(ctx)
    products["swimlanes"] = build_swimlanes(ctx)
    products["relation_type_counts"] = build_relation_type_counts(ctx)
    products.update(build_person_source_products(ctx))
    readiness_products = build_readiness_products(ctx)
    products["readiness_rows"] = readiness_products["readiness_rows"]
    products["readiness_counts"] = readiness_products["readiness_counts"]
    products["fragility"] = build_fragility(products["edge_load"], packs=ctx.packs)
    return products


def test_new_pipeline_preserves_page_content(tmp_path: Path):
    case_dir = tmp_path / "synthetic_case"
    shutil.copytree(SYNTHETIC_CASE, case_dir, ignore=shutil.ignore_patterns("__pycache__"))
    args = argparse.Namespace(
        case_dir=str(case_dir),
        out_dir=str(tmp_path / "analysis"),
        clusters_dir=None,
        include_private=False,
    )
    ctx = load_analysis_context(args)
    pages = build_analysis_chart_specs(_chart_data(_build_products(ctx)))
    signatures = {}
    for page in pages:
        contextual_page = page.model_copy(update={"case_title": ctx.case_title, "include_private": ctx.include_private})
        signatures[contextual_page.slug] = _signature(render_page(contextual_page))

    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert signatures == {key: value for key, value in expected.items() if key not in SECTION_KEYS}

    figure_keys = {
        "bipartite": "11_person_source_bipartite",
        "boundary_overlay": "08_contradiction_boundary_overlay",
        "claim_matrix": "05_claim_corroboration_matrix",
        "fragility": "04_bridge_fragility",
        "heatmap": "03_evidence_confidence_heatmap",
        "layered_graph": "02_layered_knowledge_graph",
        "layered_graph_v2": "13_layered_knowledge_graph_v2",
        "path_atlas": "07_sixdof_path_atlas",
        "readiness": "12_public_narrative_readiness",
        "sankey": "01_cluster_bridge_sankey",
        "source_quality": "06_source_quality_dashboard",
        "swimlanes": "09_temporal_cluster_swimlanes",
        "treemap": "10_relationship_type_treemap",
    }
    by_slug = {page.slug: page for page in pages}
    figure_signatures = {}
    for key, slug in figure_keys.items():
        figure = by_slug[slug].figure
        assert figure is not None
        figure_signatures[key] = svg_signature(render_svg_doc(figure))
    assert figure_signatures == expected["figures"]


def test_case_chart_and_cluster_pages_preserve_content(tmp_path: Path):
    case_dir = tmp_path / "synthetic_case"
    shutil.copytree(SYNTHETIC_CASE, case_dir, ignore=shutil.ignore_patterns("__pycache__"))
    charts_dir = tmp_path / "charts"
    clusters_dir = tmp_path / "clusters"
    export_case_charts(argparse.Namespace(case_dir=str(case_dir), out_dir=str(charts_dir), include_private=False, skip_public_gate=True))
    export_people_clusters(
        argparse.Namespace(
            case_dir=str(case_dir),
            out_dir=str(clusters_dir),
            charts_dir=str(charts_dir),
            include_private=False,
            resolution=1.0,
            seed=7,
            sigma=None,
        )
    )
    page_files = {
        "case_charts_pages": {"people_graph": charts_dir / "people_graph.html", "subcase_timelines": charts_dir / "subcase_timelines.html"},
        "clusters_pages": {"people_clusters": clusters_dir / "people_clusters.html"},
    }
    signatures = {
        section: {key: _signature(path.read_text(encoding="utf-8")) for key, path in paths.items()}
        for section, paths in page_files.items()
    }
    figures = {
        "case_charts_figures": {
            "people_graph": svg_signature(_first_svg((charts_dir / "people_graph.html").read_text(encoding="utf-8"))),
            "subcase_timeline": svg_signature(_first_svg((charts_dir / "subcase_timelines.html").read_text(encoding="utf-8"))),
        },
        "clusters_figures": {
            "people_clusters": svg_signature(_first_svg((clusters_dir / "people_clusters.html").read_text(encoding="utf-8"))),
        },
    }
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert signatures["case_charts_pages"] == expected["case_charts_pages"]
    assert signatures["clusters_pages"] == expected["clusters_pages"]
    assert figures["case_charts_figures"] == expected["case_charts_figures"]
    assert figures["clusters_figures"] == expected["clusters_figures"]
