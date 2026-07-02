"""Analysis chart export command entrypoint."""

from __future__ import annotations

import argparse
from typing import Any

from adapters.ops.evidence.reports.analysis.command.builders.bridges import build_cluster_bridges
from adapters.ops.evidence.reports.analysis.command.builders.evidence import build_evidence_products
from adapters.ops.evidence.reports.analysis.command.builders.facets.boundary import build_boundary_rows, build_readiness_products
from adapters.ops.evidence.reports.analysis.command.builders.facets.people import build_fragility, build_person_source_products
from adapters.ops.evidence.reports.analysis.command.builders.facets.relationships import build_relation_type_counts
from adapters.ops.evidence.reports.analysis.command.builders.facets.timelines import build_swimlanes
from adapters.ops.evidence.reports.analysis.command.builders.layered import build_layered_graphs
from adapters.ops.evidence.reports.analysis.command.builders.paths import build_path_atlas
from adapters.ops.evidence.reports.analysis.command.context import load_analysis_context
from adapters.ops.evidence.reports.analysis.command.output import write_analysis_outputs


def export_analysis_charts(args: argparse.Namespace) -> None:
    ctx = load_analysis_context(args)
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
    products["fragility"] = build_fragility(products["edge_load"])
    write_analysis_outputs(ctx, products)
