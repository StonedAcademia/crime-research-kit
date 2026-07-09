"""Data product assembly for case visual exports."""

from __future__ import annotations

from typing import Any

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.bridges import build_cluster_bridges
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.evidence import build_evidence_products
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.facets.boundary import build_boundary_rows, build_readiness_products
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.facets.people import build_fragility, build_person_source_products
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.facets.relationships import build_relation_type_counts
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.facets.timelines import build_swimlanes
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.layered import build_layered_graphs
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.paths import build_path_atlas
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.clustered import build_clustered_visual_products
from crime_research_kit._runtime.adapters.ops.evidence.reports.case_charts.command import _people_edges, _people_nodes, _subcase_rows

RELATIONSHIP_GRAPH_KEY = "layered_" + "v" + "2"


def build_products(ctx: AnalysisContext) -> dict[str, Any]:
    products = _analysis_products(ctx)
    products.update(_case_products(ctx))
    return products


def _analysis_products(ctx: AnalysisContext) -> dict[str, Any]:
    products: dict[str, Any] = {}
    products.update(build_cluster_bridges(ctx))
    products.update(build_path_atlas(ctx))
    products.update(build_layered_graphs(ctx))
    products["relationship_network_nodes"] = products[f"{RELATIONSHIP_GRAPH_KEY}_nodes"]
    products["relationship_network_edges"] = products[f"{RELATIONSHIP_GRAPH_KEY}_edges"]
    products.update(build_evidence_products(ctx))
    products["boundary_rows"] = build_boundary_rows(ctx)
    products["swimlanes"] = build_swimlanes(ctx)
    products["relation_type_counts"] = build_relation_type_counts(ctx)
    products.update(build_clustered_visual_products(ctx, products))
    products.update(build_person_source_products(ctx))
    readiness = build_readiness_products(ctx)
    products["readiness_rows"] = readiness["readiness_rows"]
    products["readiness_counts"] = readiness["readiness_counts"]
    products["fragility"] = build_fragility(products["edge_load"], packs=ctx.packs)
    return products


def _case_products(ctx: AnalysisContext) -> dict[str, Any]:
    people_edges = _people_edges(ctx.relationships, ctx.events, ctx.event_links, ctx.people_by_id)
    return {
        "people_nodes": _people_nodes(ctx.people, ctx.include_private, ctx.claim_by_id),
        "people_edges": people_edges,
        "timeline_rows": _subcase_rows(ctx.events, ctx.claim_by_id, ctx.source_by_id)[0],
    }
