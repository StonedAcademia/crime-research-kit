"""New analysis page models preserve legacy page content signatures."""

from __future__ import annotations

import argparse
import json
import re
import shutil
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
from adapters.ops.evidence.reports.analysis.pages.render import render_page
from adapters.ops.evidence.reports.analysis.pages.specs import build_analysis_chart_specs


ROOT = Path(__file__).resolve().parents[5]
SYNTHETIC_CASE = ROOT / "data" / "examples" / "synthetic_case"
FIXTURE = Path(__file__).with_name("analysis_page_signatures.json")


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
    assert signatures == expected
