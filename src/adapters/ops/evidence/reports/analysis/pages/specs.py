"""Chart specification assembly for analysis exports."""

from __future__ import annotations

from typing import Any

from core.models.reports import ReportPage, SvgDoc, TableBlock

from adapters.ops.evidence.reports.analysis.pages.render import filter_terms
from adapters.ops.evidence.reports.analysis.svg.facets import (
    render_bipartite_svg,
    render_boundary_overlay_svg,
    render_path_atlas_svg,
    render_swimlanes_svg,
    render_treemap_svg,
)
from adapters.ops.evidence.reports.analysis.svg.matrix import (
    build_claim_matrix_figure,
    build_fragility_figure,
    build_heatmap_figure,
    build_readiness_figure,
    build_source_quality_figure,
)
from adapters.ops.evidence.reports.analysis.svg.network.bridges import render_sankey_svg
from adapters.ops.evidence.reports.analysis.svg.network.layers import (
    render_layered_graph_svg,
    render_layered_graph_v2_svg,
)
from adapters.ops.evidence.ledger.records import flatten


def _table_block(rows: list[dict[str, Any]], columns: list[str], limit: int) -> TableBlock:
    return TableBlock(
        columns=columns,
        rows=[{column: flatten(row.get(column)) for column in columns} for row in rows],
        limit=limit,
    )


def _page(
    number: int,
    slug: str,
    title: str,
    summary: str,
    figure: SvgDoc | str,
    rows: list[dict[str, Any]],
    columns: list[str],
    limit: int,
    filters: list[str],
) -> ReportPage:
    return ReportPage(
        slug=f"{number:02d}_{slug}",
        title=title,
        case_title="",
        summary=summary,
        filters=filters,
        figure=figure if isinstance(figure, SvgDoc) else None,
        legacy_figure_svg=figure if isinstance(figure, str) else "",
        table=_table_block(rows, columns, limit),
    )


def _page_number(page: ReportPage) -> int:
    return int(page.slug.split("_", 1)[0])


def build_analysis_chart_specs(chart_data: dict[str, Any]) -> list[ReportPage]:
    return sorted([
        _page(
            1,
            "cluster_bridge_sankey",
            "Cluster Bridge Sankey",
            "Audited inter-cluster bridge flow with category and lead-context links visually separated.",
            render_sankey_svg(chart_data["sankey_nodes"], chart_data["cluster_bridge_links"]),
            chart_data["cluster_bridges"],
            ["src_cluster", "dst_cluster", "bridge_class", "hops", "path", "statuses"],
            12,
            filter_terms(chart_data["cluster_bridge_links"], ["public_readiness", "bridge_class"]),
        ),
        _page(
            2,
            "layered_knowledge_graph",
            "Layered Knowledge Graph",
            "Layered graph separating people, events, organizations, institutions, and context nodes.",
            render_layered_graph_svg(chart_data["layered_nodes"], chart_data["layered_edges"]),
            chart_data["layered_edges"],
            ["src_label", "dst_label", "edge_type", "relation_type", "relationship_class", "status", "source_count"],
            18,
            filter_terms(chart_data["layered_edges"], ["status", "edge_type", "relation_type", "relationship_class"]),
        ),
        _page(
            13,
            "layered_knowledge_graph_v2",
            "Layered Knowledge Graph v2",
            "Evidence-navigation graph with explicit layers, source grades, public-readiness state, caveats, and cluster context.",
            render_layered_graph_v2_svg(chart_data["layered_v2_nodes"], chart_data["layered_v2_edges"]),
            chart_data["layered_v2_edges"],
            ["src_label", "dst_label", "relationship_class", "bridge_class", "readiness", "source_count", "caveat"],
            18,
            filter_terms(chart_data["layered_v2_edges"], ["readiness", "bridge_class", "relationship_class", "best_source_grade", "caveat"]),
        ),
        _page(
            3,
            "evidence_confidence_heatmap",
            "Evidence Confidence Heatmap",
            "Claim-type by status heatmap, with cell intensity tied to average confidence.",
            build_heatmap_figure(chart_data["heatmap_aggregate"]),
            chart_data["claim_heatmap"],
            ["claim_id", "status", "confidence", "source_count", "best_source_grade", "readiness"],
            18,
            filter_terms(chart_data["claim_heatmap"], ["status", "claim_type", "readiness"]),
        ),
        _page(
            4,
            "bridge_fragility",
            "Bridge Fragility Chart",
            "Load-bearing bridge records plotted against fragility score.",
            build_fragility_figure(chart_data["fragility"]),
            chart_data["fragility"],
            ["record_id", "relationship_class", "load_bearing_score", "fragility_score", "fragility_tier", "bridge_class"],
            18,
            filter_terms(chart_data["fragility"], ["fragility_tier", "bridge_class", "relationship_class", "status"]),
        ),
        _page(
            5,
            "claim_corroboration_matrix",
            "Claim Corroboration Matrix",
            "Claim-source matrix colored by source grade and preserving boundary/contradiction markers.",
            build_claim_matrix_figure(chart_data["claim_matrix"]),
            chart_data["claim_matrix"],
            ["claim_id", "source_id", "source_grade", "source_type", "claim_status"],
            20,
            filter_terms(chart_data["claim_matrix"], ["source_grade", "claim_status", "source_role"]),
        ),
        _page(
            6,
            "source_quality_dashboard",
            "Source Quality Dashboard",
            "Source-grade distribution with coverage footprint across claims, events, relationships, and people.",
            build_source_quality_figure(chart_data["source_grade_counts"], chart_data["source_dashboard"]),
            chart_data["source_dashboard"],
            ["source_id", "reliability_grade", "claim_count", "event_count", "relationship_count", "nonpublic_record_count"],
            18,
            filter_terms(chart_data["source_dashboard"], ["reliability_grade", "source_type", "publisher"]),
        ),
        _page(
            7,
            "sixdof_path_atlas",
            "6DOF Path Atlas",
            "Hop-distance atlas from the anchor person, with paths over six hops explicitly marked.",
            render_path_atlas_svg(chart_data["path_atlas"]),
            chart_data["path_atlas"],
            ["target_person", "hops", "over_six_hops", "weakest_status", "relationship_classes"],
            18,
            filter_terms(chart_data["path_atlas"], ["weakest_status", "bridge_classes", "relationship_classes", "over_six_hops"]),
        ),
        _page(
            8,
            "contradiction_boundary_overlay",
            "Contradiction / Boundary Overlay",
            "Boundary and contradiction markers grouped by record type and status.",
            render_boundary_overlay_svg(chart_data["boundary_rows"]),
            chart_data["boundary_rows"],
            ["record_id", "record_type", "status", "claim_type", "boundary_kind", "relationship_class", "summary"],
            18,
            filter_terms(chart_data["boundary_rows"], ["record_type", "status", "boundary_kind", "relationship_class"]),
        ),
        _page(
            9,
            "temporal_cluster_swimlanes",
            "Temporal Cluster Swimlanes",
            "Dated event-link markers placed on one swimlane per cluster.",
            render_swimlanes_svg(chart_data["swimlanes"]),
            chart_data["swimlanes"],
            ["cluster_id", "start_date", "event_id", "event_title", "relationship_class", "status", "source_count"],
            18,
            filter_terms(chart_data["swimlanes"], ["cluster_id", "status", "event_link_status", "relation_type", "relationship_class"]),
        ),
        _page(
            10,
            "relationship_type_treemap",
            "Relationship-Class Treemap",
            "Weighted relationship/event-link buckets grouped by lineage, diffusion, personnel, narrative, contested, and hypothesis classes.",
            render_treemap_svg(chart_data["relation_type_counts"]),
            chart_data["relation_type_counts"],
            ["relationship_class", "relation_family", "relation_type", "status", "weighted_count", "row_count"],
            18,
            filter_terms(chart_data["relation_type_counts"], ["relationship_class", "relation_family", "status", "public_scope"]),
        ),
        _page(
            11,
            "person_source_bipartite",
            "Person-Source Bipartite Graph",
            "Top person-source evidence links derived from direct, claim, relationship, event, and event-link paths.",
            render_bipartite_svg(chart_data["person_source_nodes"], chart_data["person_source"]),
            chart_data["person_source"],
            ["person_name", "source_id", "source_grade", "contexts"],
            18,
            filter_terms(chart_data["person_source"], ["source_grade", "contexts", "public_evidence_state"]),
        ),
        _page(
            12,
            "public_narrative_readiness",
            "Public Narrative Readiness",
            "Readiness tiers for public narration, with privacy and boundary gates preserved.",
            build_readiness_figure(chart_data["readiness_counts"]),
            chart_data["readiness_counts"],
            ["readiness", "count"],
            12,
            filter_terms(chart_data["readiness_counts"], ["readiness"]),
        ),
    ], key=_page_number)
