"""Package metadata for case visual exports."""

from __future__ import annotations

import datetime as dt
from typing import Any

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.context import AnalysisContext

CONSOLE_SLUGS = (
    "evidence_readiness",
    "cluster_overview",
    "cluster_detail",
    "source_subproject",
    "relationship_network",
    "timeline_movement",
    "claim_source_matrix",
)
RETIRED_VISUAL_ARTIFACTS = ("deck.html", "explorer.html")
VISUAL_NAV_GROUPS = (
    {"id": "evidence_overview", "title": "Evidence Overview", "slugs": ("evidence_readiness", "cluster_overview", "claim_source_matrix")},
    {"id": "relationship_graphs", "title": "Relationship Graphs", "slugs": ("cluster_detail", "relationship_network")},
    {"id": "timeline_source_map", "title": "Timeline & Source Map", "slugs": ("timeline_movement", "source_subproject")},
)


def build_package(ctx: AnalysisContext, products: dict[str, Any], *, generated: str | None = None) -> dict[str, Any]:
    generated = generated or dt.datetime.now(dt.timezone.utc).isoformat()
    consoles = _consoles(ctx, products)
    for console in consoles.values():
        console["include_private"] = ctx.include_private
    package = {
        "case_title": ctx.case_title,
        "include_private": ctx.include_private,
        "generated_at": generated,
        "asset_version": _asset_version(generated),
        "scope": "internal review: public and private/internal rows" if ctx.include_private else "public-export rows only",
        "counts": {"sources": len(ctx.sources), "entities": len(ctx.entities), "claims": len(ctx.claims), "events": len(ctx.events), "relationships": len(ctx.relationships)},
        "warnings": _warnings(ctx, products),
        "consoles": consoles,
        "nav_groups": _nav_groups(consoles),
        "audit": _audit(products),
        "cluster_policy": products["cluster_policy"],
        "contains_private_bundle": False,
        "default_mode": "public",
        "available_modes": ["public"],
    }
    package["modes"] = {"public": _mode_metadata(package, data_prefix="data", audit_prefix="audit", label="Public")}
    return package


def bundle_package(public_package: dict[str, Any], private_package: dict[str, Any]) -> dict[str, Any]:
    package = dict(public_package)
    package.update({
        "include_private": True,
        "private_package": private_package,
        "contains_private_bundle": True,
        "available_modes": ["public", "private"],
    })
    package["modes"] = {
        "public": _mode_metadata(public_package, data_prefix="data", audit_prefix="audit", label="Public"),
        "private": _mode_metadata(private_package, data_prefix="data/private", audit_prefix="audit/private", label="Internal"),
    }
    return package


def manifest(package: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_title": package["case_title"],
        "generated_at": package["generated_at"],
        "include_private": package["include_private"],
        "default_mode": package.get("default_mode", "public"),
        "available_modes": package.get("available_modes", ["public"]),
        "contains_private_bundle": bool(package.get("private_package")),
        "modes": package.get("modes", {"public": _mode_metadata(package, data_prefix="data", audit_prefix="audit", label="Public")}),
        "scope": package["scope"],
        "artifacts": package["artifacts"],
        "warnings": package["warnings"],
        "main": "index.html",
        "consoles": list(CONSOLE_SLUGS),
        "nav_groups": [{"id": group["id"], "title": group["title"], "consoles": [item["slug"] for item in group["entries"]]} for group in package["nav_groups"]],
        "cluster_policy": package["cluster_policy"],
    }


def _consoles(ctx: AnalysisContext, products: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "evidence_readiness": _console("evidence_readiness", "Evidence Readiness", "d3-readiness", {"readiness": products["readiness_counts"], "sources": products["source_grade_count_rows"], "confidence": products["heatmap_aggregate"], "boundaries": products["boundary_rows"][:80]}, ["readiness_rows.csv", "source_quality.csv", "claim_confidence.csv", "boundaries.csv"]),
        "cluster_overview": _console("cluster_overview", "Cluster Overview", "d3-cluster-overview", {"clusters": products["cluster_overview"], "facets": products["facet_counts"], "hubs": products["hub_nodes"]}, ["cluster_overview.csv", "facet_counts.csv", "hub_nodes.csv"]),
        "cluster_detail": _console("cluster_detail", "Cluster Detail Graph", "cytoscape-clustered-network", {"nodes": products["relationship_network_nodes"], "edges": products["cluster_detail_edges"], "clusters": products["cluster_overview"], "hubs": products["hub_nodes"]}, ["relationship_nodes.csv", "cluster_detail_edges.csv"]),
        "source_subproject": _console("source_subproject", "Source-to-Subproject Map", "d3-source-subproject", {"edges": products["source_subproject_edges"], "matrix": products["subproject_matrix"], "clusters": products["cluster_overview"]}, ["source_subproject_edges.csv", "subproject_matrix.csv"]),
        "relationship_network": _console("relationship_network", "Relationship Network", "cytoscape-network", {"nodes": products["relationship_network_nodes"], "edges": products["relationship_network_edges"], "clusters": products["cluster_overview"], "facets": products["facet_counts"], "people": products["people_nodes"], "people_edges": products["people_edges"]}, ["relationship_nodes.csv", "relationship_edges.csv", "people_edges.csv"]),
        "timeline_movement": _console("timeline_movement", "Timeline Movement", "d3-timeline", {"events": products["cluster_timeline"], "subcases": products["timeline_rows"], "paths": products["path_atlas"]}, ["cluster_timeline.csv", "path_atlas.csv"]),
        "claim_source_matrix": _console("claim_source_matrix", "Claim Source Matrix", "d3-matrix", {"claims": products["claim_heatmap"], "matrix": products["claim_matrix"], "claim_edges": products["claim_edge_rows"]}, ["claim_source_matrix.csv", "claim_edges.csv"]),
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
        groups.append({"id": group["id"], "title": group["title"], "slugs": list(group["slugs"]), "entries": entries})
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


def _mode_metadata(package: dict[str, Any], *, data_prefix: str, audit_prefix: str, label: str) -> dict[str, Any]:
    return {"label": label, "include_private": package["include_private"], "scope": package["scope"], "warnings": package["warnings"], "data_prefix": data_prefix, "audit_prefix": audit_prefix}


def _asset_version(value: str) -> str:
    return "".join(char for char in value if char.isalnum())
