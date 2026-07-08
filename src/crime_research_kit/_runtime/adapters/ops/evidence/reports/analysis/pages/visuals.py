"""Consolidated case visual export package."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from crime_research_kit._runtime.adapters.ops.evidence.ledger.records import write_csv
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.bridges import build_cluster_bridges
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.evidence import build_evidence_products
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.facets.boundary import build_boundary_rows, build_readiness_products
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.facets.people import build_fragility, build_person_source_products
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.facets.relationships import build_relation_type_counts
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.facets.timelines import build_swimlanes
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.layered import build_layered_graphs
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.paths import build_path_atlas
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.context import AnalysisContext, load_analysis_context
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.clustered import build_clustered_visual_products
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.render import _environment, write_html
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.visual_assets import write_visual_assets
from crime_research_kit._runtime.adapters.ops.evidence.reports.case_charts.command import _people_edges, _people_nodes, _subcase_rows
from crime_research_kit._runtime.core.casefile import case_path

CONSOLE_SLUGS = (
    "evidence_readiness",
    "cluster_overview",
    "cluster_detail",
    "source_subproject",
    "subproject_matrix",
    "relationship_network",
    "timeline_movement",
    "claim_source_matrix",
)
RELATIONSHIP_GRAPH_KEY = "layered_" + "v" + "2"


def export_case_visuals(args: argparse.Namespace) -> None:
    include_private = bool(args.include_private)
    cdir = case_path(args.case_dir)
    requested_out = Path(args.out_dir).expanduser().resolve() if args.out_dir else None
    out = requested_out or cdir / ("exports/internal/visuals" if include_private else "exports/visuals")
    context_args = argparse.Namespace(
        case_dir=args.case_dir,
        out_dir=str(out),
        clusters_dir=getattr(args, "clusters_dir", None),
        include_private=include_private,
        gate_name="export-case-visuals",
    )
    ctx = load_analysis_context(context_args)
    products = _analysis_products(ctx)
    products.update(_case_products(ctx))
    package = _package(ctx, products)
    _write_audit(ctx.out / "audit", package["audit"])
    _write_html_package(ctx.out, package)
    print(f"Exported case visuals to {ctx.out}")


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


def _package(ctx: AnalysisContext, products: dict[str, Any]) -> dict[str, Any]:
    generated = dt.datetime.now(dt.timezone.utc).isoformat()
    audit = _audit(products)
    consoles = {
        "evidence_readiness": _console("evidence_readiness", "Evidence Readiness", "d3-readiness", {
            "readiness": products["readiness_counts"],
            "sources": products["source_grade_count_rows"],
            "confidence": products["heatmap_aggregate"],
            "boundaries": products["boundary_rows"][:80],
        }, ["readiness_rows.csv", "source_quality.csv", "claim_confidence.csv", "boundaries.csv"]),
        "cluster_overview": _console("cluster_overview", "Cluster Overview", "d3-cluster-overview", {
            "clusters": products["cluster_overview"],
            "facets": products["facet_counts"],
            "hubs": products["hub_nodes"],
        }, ["cluster_overview.csv", "facet_counts.csv", "hub_nodes.csv"]),
        "cluster_detail": _console("cluster_detail", "Cluster Detail Graph", "cytoscape-clustered-network", {
            "nodes": products["relationship_network_nodes"],
            "edges": products["cluster_detail_edges"],
            "clusters": products["cluster_overview"],
            "hubs": products["hub_nodes"],
        }, ["relationship_nodes.csv", "cluster_detail_edges.csv"]),
        "source_subproject": _console("source_subproject", "Source-to-Subproject Map", "d3-source-subproject", {
            "edges": products["source_subproject_edges"],
            "matrix": products["subproject_matrix"],
            "clusters": products["cluster_overview"],
        }, ["source_subproject_edges.csv", "subproject_matrix.csv"]),
        "subproject_matrix": _console("subproject_matrix", "Subproject Matrix", "d3-subproject-matrix", {
            "matrix": products["subproject_matrix"],
            "clusters": products["cluster_overview"],
        }, ["subproject_matrix.csv", "cluster_overview.csv"]),
        "relationship_network": _console("relationship_network", "Relationship Network", "cytoscape-network", {
            "nodes": products["relationship_network_nodes"],
            "edges": products["relationship_network_edges"],
            "people": products["people_nodes"],
            "people_edges": products["people_edges"],
        }, ["relationship_nodes.csv", "relationship_edges.csv", "people_edges.csv"]),
        "timeline_movement": _console("timeline_movement", "Timeline Movement", "d3-timeline", {
            "events": products["cluster_timeline"],
            "subcases": products["timeline_rows"],
            "paths": products["path_atlas"],
        }, ["cluster_timeline.csv", "path_atlas.csv"]),
        "claim_source_matrix": _console("claim_source_matrix", "Claim Source Matrix", "d3-matrix", {
            "claims": products["claim_heatmap"],
            "matrix": products["claim_matrix"],
            "claim_edges": products["claim_edge_rows"],
        }, ["claim_source_matrix.csv", "claim_edges.csv"]),
    }
    for console in consoles.values():
        console["include_private"] = ctx.include_private
    return {
        "case_title": ctx.case_title,
        "include_private": ctx.include_private,
        "generated_at": generated,
        "scope": "internal review: public and private/internal rows" if ctx.include_private else "public-export rows only",
        "counts": {"sources": len(ctx.sources), "entities": len(ctx.entities), "claims": len(ctx.claims), "events": len(ctx.events), "relationships": len(ctx.relationships)},
        "warnings": _warnings(ctx, products),
        "consoles": consoles,
        "audit": audit,
        "cluster_policy": products["cluster_policy"],
    }


def _console(slug: str, title: str, kind: str, data: dict[str, Any], audit_files: list[str]) -> dict[str, Any]:
    return {"slug": slug, "title": title, "kind": kind, "data": data, "audit_files": audit_files}


def _audit(products: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {
        "readiness_rows": products["readiness_rows"],
        "source_quality": products["source_dashboard"],
        "claim_confidence": products["claim_heatmap"],
        "boundaries": products["boundary_rows"],
        "relationship_nodes": products["relationship_network_nodes"],
        "relationship_edges": products["relationship_network_edges"],
        "cluster_overview": products["cluster_overview"],
        "cluster_detail_edges": products["cluster_detail_edges"],
        "source_subproject_edges": products["source_subproject_edges"],
        "subproject_matrix": products["subproject_matrix"],
        "cluster_timeline": products["cluster_timeline"],
        "hub_nodes": products["hub_nodes"],
        "facet_counts": products["facet_counts"],
        "people_edges": products["people_edges"],
        "timeline_events": products["swimlanes"],
        "path_atlas": products["path_atlas"],
        "claim_source_matrix": products["claim_matrix"],
        "claim_edges": products["claim_edge_rows"],
    }


def _warnings(ctx: AnalysisContext, products: dict[str, Any]) -> list[str]:
    warnings = []
    if ctx.include_private:
        warnings.append("Internal review export includes private or nonpublic rows.")
    if not products["relationship_network_edges"]:
        warnings.append("Relationship network has no source-supported edges.")
    if not products["timeline_rows"]:
        warnings.append("Timeline console has no dated case events.")
    return warnings


def _write_audit(out: Path, audit: dict[str, list[dict[str, Any]]]) -> None:
    for name, rows in audit.items():
        columns = sorted({column for row in rows for column in row}) or ["empty"]
        write_csv(out / f"{name}.csv", rows, columns)


def _write_html_package(out: Path, package: dict[str, Any]) -> None:
    artifacts = ["deck.html", "explorer.html"]
    for slug in CONSOLE_SLUGS:
        artifacts.append(f"consoles/{slug}.html")
    asset_artifacts = write_visual_assets(out, package)
    package["artifacts"] = artifacts + asset_artifacts + [f"audit/{name}.csv" for name in sorted(package["audit"])]
    write_html(out / "deck.html", _render("layouts/visual_deck.html.j2", package=package))
    write_html(out / "explorer.html", _render("layouts/visual.html.j2", package=package, console=None, asset_prefix=""))
    for slug, console in package["consoles"].items():
        write_html(out / "consoles" / f"{slug}.html", _render("layouts/visual.html.j2", package=package, console=console, asset_prefix="../"))
    (out / "manifest.json").write_text(json.dumps(_manifest(package), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _render(template: str, **data: Any) -> str:
    return _environment().get_template(template).render(**data)


def _manifest(package: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_title": package["case_title"],
        "generated_at": package["generated_at"],
        "include_private": package["include_private"],
        "scope": package["scope"],
        "artifacts": package["artifacts"],
        "warnings": package["warnings"],
        "consoles": list(CONSOLE_SLUGS),
        "cluster_policy": package["cluster_policy"],
    }
