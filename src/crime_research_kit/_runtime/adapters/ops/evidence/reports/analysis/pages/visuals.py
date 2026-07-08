"""Consolidated case visual export package."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import shutil
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
from crime_research_kit._runtime.adapters.ops.evidence.reports.common import reject_legacy_export_dir
from crime_research_kit._runtime.core.casefile import case_path

CONSOLE_SLUGS = (
    "evidence_readiness",
    "cluster_overview",
    "cluster_detail",
    "source_subproject",
    "relationship_network",
    "timeline_movement",
    "claim_source_matrix",
)
RELATIONSHIP_GRAPH_KEY = "layered_" + "v" + "2"
RETIRED_VISUAL_ARTIFACTS = ("deck.html", "explorer.html")
VISUAL_NAV_GROUPS = (
    {
        "id": "evidence_overview",
        "title": "Evidence Overview",
        "slugs": ("evidence_readiness", "cluster_overview", "claim_source_matrix"),
    },
    {
        "id": "relationship_graphs",
        "title": "Relationship Graphs",
        "slugs": ("cluster_detail", "relationship_network"),
    },
    {
        "id": "timeline_source_map",
        "title": "Timeline & Source Map",
        "slugs": ("timeline_movement", "source_subproject"),
    },
)


def export_case_visuals(args: argparse.Namespace) -> None:
    include_private = bool(args.include_private)
    cdir = case_path(args.case_dir)
    requested_out = Path(args.out_dir).expanduser().resolve() if args.out_dir else None
    out = requested_out or cdir / "exports" / "internal" / "visuals"
    reject_legacy_export_dir(out)
    if include_private:
        private_ctx = _load_visual_context(args, out, include_private=True)
        public_ctx = _load_visual_context(args, out, include_private=False, skip_public_gate=True)
        generated = dt.datetime.now(dt.timezone.utc).isoformat()
        public_package = _package(public_ctx, _products(public_ctx), generated=generated)
        private_package = _package(private_ctx, _products(private_ctx), generated=generated)
        package = _bundle_package(public_package, private_package)
        ctx = private_ctx
    else:
        ctx = _load_visual_context(args, out, include_private=False)
        package = _package(ctx, _products(ctx))
    _write_audit(ctx.out / "audit", package["audit"])
    private_package = package.get("private_package")
    if private_package:
        _write_audit(ctx.out / "audit" / "private", private_package["audit"])
    else:
        shutil.rmtree(ctx.out / "audit" / "private", ignore_errors=True)
    _write_html_package(ctx.out, package)
    print(f"Exported case visuals to {ctx.out}")


def _load_visual_context(args: argparse.Namespace, out: Path, *, include_private: bool, skip_public_gate: bool = False) -> AnalysisContext:
    return load_analysis_context(
        argparse.Namespace(
            case_dir=args.case_dir,
            out_dir=str(out),
            clusters_dir=getattr(args, "clusters_dir", None),
            include_private=include_private,
            gate_name="export-case-visuals",
            skip_public_gate=skip_public_gate,
        )
    )


def _products(ctx: AnalysisContext) -> dict[str, Any]:
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


def _package(ctx: AnalysisContext, products: dict[str, Any], *, generated: str | None = None) -> dict[str, Any]:
    generated = generated or dt.datetime.now(dt.timezone.utc).isoformat()
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
        "relationship_network": _console("relationship_network", "Relationship Network", "cytoscape-network", {
            "nodes": products["relationship_network_nodes"],
            "edges": products["relationship_network_edges"],
            "clusters": products["cluster_overview"],
            "facets": products["facet_counts"],
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
    nav_groups = _nav_groups(consoles)
    package = {
        "case_title": ctx.case_title,
        "include_private": ctx.include_private,
        "generated_at": generated,
        "asset_version": _asset_version(generated),
        "scope": "internal review: public and private/internal rows" if ctx.include_private else "public-export rows only",
        "counts": {"sources": len(ctx.sources), "entities": len(ctx.entities), "claims": len(ctx.claims), "events": len(ctx.events), "relationships": len(ctx.relationships)},
        "warnings": _warnings(ctx, products),
        "consoles": consoles,
        "nav_groups": nav_groups,
        "audit": audit,
        "cluster_policy": products["cluster_policy"],
    }
    package["contains_private_bundle"] = False
    package["default_mode"] = "public"
    package["available_modes"] = ["public"]
    package["modes"] = {
        "public": _mode_metadata(package, data_prefix="data", audit_prefix="audit", label="Public"),
    }
    return package


def _bundle_package(public_package: dict[str, Any], private_package: dict[str, Any]) -> dict[str, Any]:
    package = dict(public_package)
    package["include_private"] = True
    package["private_package"] = private_package
    package["contains_private_bundle"] = True
    package["default_mode"] = "public"
    package["available_modes"] = ["public", "private"]
    package["modes"] = {
        "public": _mode_metadata(public_package, data_prefix="data", audit_prefix="audit", label="Public"),
        "private": _mode_metadata(private_package, data_prefix="data/private", audit_prefix="audit/private", label="Internal"),
    }
    return package


def _mode_metadata(package: dict[str, Any], *, data_prefix: str, audit_prefix: str, label: str) -> dict[str, Any]:
    return {
        "label": label,
        "include_private": package["include_private"],
        "scope": package["scope"],
        "warnings": package["warnings"],
        "data_prefix": data_prefix,
        "audit_prefix": audit_prefix,
    }


def _console(slug: str, title: str, kind: str, data: dict[str, Any], audit_files: list[str]) -> dict[str, Any]:
    return {"slug": slug, "title": title, "kind": kind, "data": data, "audit_files": audit_files}


def _nav_groups(consoles: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    groups = []
    for group in VISUAL_NAV_GROUPS:
        entries = []
        for slug in group["slugs"]:
            console = consoles.get(slug)
            if not console:
                continue
            console["nav_group_id"] = group["id"]
            console["nav_group_title"] = group["title"]
            entries.append(console)
        groups.append({
            "id": group["id"],
            "title": group["title"],
            "slugs": list(group["slugs"]),
            "entries": entries,
        })
    return groups


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
    _remove_retired_visual_artifacts(out)
    artifacts = ["index.html"]
    for slug in CONSOLE_SLUGS:
        artifacts.append(f"consoles/{slug}.html")
    asset_artifacts = write_visual_assets(out, package)
    audit_artifacts = [f"audit/{name}.csv" for name in sorted(package["audit"])]
    private_package = package.get("private_package")
    if private_package:
        audit_artifacts.extend(f"audit/private/{name}.csv" for name in sorted(private_package["audit"]))
    package["artifacts"] = artifacts + asset_artifacts + audit_artifacts
    write_html(out / "index.html", _render("layouts/visual.html.j2", package=package, console=None, asset_prefix=""))
    for slug, console in package["consoles"].items():
        write_html(out / "consoles" / f"{slug}.html", _render("layouts/visual.html.j2", package=package, console=console, asset_prefix="../"))
    (out / "manifest.json").write_text(json.dumps(_manifest(package), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _remove_retired_visual_artifacts(out: Path) -> None:
    for relative in RETIRED_VISUAL_ARTIFACTS:
        (out / relative).unlink(missing_ok=True)


def _render(template: str, **data: Any) -> str:
    return _environment().get_template(template).render(**data)


def _manifest(package: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_title": package["case_title"],
        "generated_at": package["generated_at"],
        "include_private": package["include_private"],
        "default_mode": package.get("default_mode", "public"),
        "available_modes": package.get("available_modes", ["public"]),
        "contains_private_bundle": bool(package.get("private_package")),
        "modes": package.get(
            "modes",
            {
                "public": _mode_metadata(package, data_prefix="data", audit_prefix="audit", label="Public"),
            },
        ),
        "scope": package["scope"],
        "artifacts": package["artifacts"],
        "warnings": package["warnings"],
        "main": "index.html",
        "consoles": list(CONSOLE_SLUGS),
        "nav_groups": [
            {"id": group["id"], "title": group["title"], "consoles": [item["slug"] for item in group["entries"]]}
            for group in package["nav_groups"]
        ],
        "cluster_policy": package["cluster_policy"],
    }


def _asset_version(value: str) -> str:
    return "".join(char for char in value if char.isalnum())
