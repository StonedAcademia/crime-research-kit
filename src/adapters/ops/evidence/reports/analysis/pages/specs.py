"""Chart specification assembly for analysis exports."""

from __future__ import annotations

from typing import Any

from adapters.ops.evidence.reports.analysis.pages.render import chart_row_table, filter_terms
from adapters.ops.evidence.reports.analysis.svg.facets import (
    render_bipartite_svg,
    render_boundary_overlay_svg,
    render_path_atlas_svg,
    render_swimlanes_svg,
    render_treemap_svg,
)
from adapters.ops.evidence.reports.analysis.svg.matrix import (
    render_claim_matrix_svg,
    render_fragility_svg,
    render_heatmap_svg,
    render_readiness_svg,
    render_source_quality_svg,
)
from adapters.ops.evidence.reports.analysis.svg.network.bridges import render_sankey_svg
from adapters.ops.evidence.reports.analysis.svg.network.layers import (
    render_layered_graph_svg,
    render_layered_graph_v2_svg,
)


def build_analysis_chart_specs(chart_data: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted([
        {
            "number": 1,
            "title": "Cluster Bridge Sankey",
            "filename": "01_cluster_bridge_sankey.html",
            "description": "Audited inter-cluster bridge flow with category and lead-context links visually separated.",
            "csvs": "cluster_bridge_sankey_nodes.csv / cluster_bridge_sankey_links.csv",
            "chart_html": render_sankey_svg(chart_data["sankey_nodes"], chart_data["cluster_bridge_links"]),
            "preview_html": chart_row_table(chart_data["cluster_bridges"], ["src_cluster", "dst_cluster", "bridge_class", "hops", "path", "statuses"], 12),
            "filters": filter_terms(chart_data["cluster_bridge_links"], ["public_readiness", "bridge_class"]),
        },
        {
            "number": 2,
            "title": "Layered Knowledge Graph",
            "filename": "02_layered_knowledge_graph.html",
            "description": "Layered graph separating people, events, organizations, institutions, and context nodes.",
            "csvs": "layered_knowledge_graph_nodes.csv / layered_knowledge_graph_edges.csv",
            "chart_html": render_layered_graph_svg(chart_data["layered_nodes"], chart_data["layered_edges"]),
            "preview_html": chart_row_table(chart_data["layered_edges"], ["src_label", "dst_label", "edge_type", "relation_type", "relationship_class", "status", "source_count"], 18),
            "filters": filter_terms(chart_data["layered_edges"], ["status", "edge_type", "relation_type", "relationship_class"]),
        },
        {
            "number": 13,
            "title": "Layered Knowledge Graph v2",
            "filename": "13_layered_knowledge_graph_v2.html",
            "description": "Evidence-navigation graph with explicit layers, source grades, public-readiness state, caveats, and cluster context.",
            "csvs": "layered_knowledge_graph_v2_nodes.csv / layered_knowledge_graph_v2_edges.csv / layered_knowledge_graph_v2_layers.csv",
            "chart_html": render_layered_graph_v2_svg(chart_data["layered_v2_nodes"], chart_data["layered_v2_edges"]),
            "preview_html": chart_row_table(chart_data["layered_v2_edges"], ["src_label", "dst_label", "relationship_class", "bridge_class", "readiness", "source_count", "caveat"], 18),
            "filters": filter_terms(chart_data["layered_v2_edges"], ["readiness", "bridge_class", "relationship_class", "best_source_grade", "caveat"]),
        },
        {
            "number": 3,
            "title": "Evidence Confidence Heatmap",
            "filename": "03_evidence_confidence_heatmap.html",
            "description": "Claim-type by status heatmap, with cell intensity tied to average confidence.",
            "csvs": "evidence_confidence_heatmap.csv / evidence_confidence_heatmap_aggregate.csv",
            "chart_html": render_heatmap_svg(chart_data["heatmap_aggregate"]),
            "preview_html": chart_row_table(chart_data["claim_heatmap"], ["claim_id", "status", "confidence", "source_count", "best_source_grade", "readiness"], 18),
            "filters": filter_terms(chart_data["claim_heatmap"], ["status", "claim_type", "readiness"]),
        },
        {
            "number": 4,
            "title": "Bridge Fragility Chart",
            "filename": "04_bridge_fragility.html",
            "description": "Load-bearing bridge records plotted against fragility score.",
            "csvs": "bridge_fragility.csv / bridge_fragility_segments.csv",
            "chart_html": render_fragility_svg(chart_data["fragility"]),
            "preview_html": chart_row_table(chart_data["fragility"], ["record_id", "relationship_class", "load_bearing_score", "fragility_score", "fragility_tier", "bridge_class"], 18),
            "filters": filter_terms(chart_data["fragility"], ["fragility_tier", "bridge_class", "relationship_class", "status"]),
        },
        {
            "number": 5,
            "title": "Claim Corroboration Matrix",
            "filename": "05_claim_corroboration_matrix.html",
            "description": "Claim-source matrix colored by source grade and preserving boundary/contradiction markers.",
            "csvs": "claim_corroboration_matrix.csv / claim_corroboration_edges.csv",
            "chart_html": render_claim_matrix_svg(chart_data["claim_matrix"]),
            "preview_html": chart_row_table(chart_data["claim_matrix"], ["claim_id", "source_id", "source_grade", "source_type", "claim_status"], 20),
            "filters": filter_terms(chart_data["claim_matrix"], ["source_grade", "claim_status", "source_role"]),
        },
        {
            "number": 6,
            "title": "Source Quality Dashboard",
            "filename": "06_source_quality_dashboard.html",
            "description": "Source-grade distribution with coverage footprint across claims, events, relationships, and people.",
            "csvs": "source_quality_dashboard.csv",
            "chart_html": render_source_quality_svg(chart_data["source_grade_counts"], chart_data["source_dashboard"]),
            "preview_html": chart_row_table(chart_data["source_dashboard"], ["source_id", "reliability_grade", "claim_count", "event_count", "relationship_count", "nonpublic_record_count"], 18),
            "filters": filter_terms(chart_data["source_dashboard"], ["reliability_grade", "source_type", "publisher"]),
        },
        {
            "number": 7,
            "title": "6DOF Path Atlas",
            "filename": "07_sixdof_path_atlas.html",
            "description": "Hop-distance atlas from the anchor person, with paths over six hops explicitly marked.",
            "csvs": "sixdof_path_atlas.csv / sixdof_path_segments.csv",
            "chart_html": render_path_atlas_svg(chart_data["path_atlas"]),
            "preview_html": chart_row_table(chart_data["path_atlas"], ["target_person", "hops", "over_six_hops", "weakest_status", "relationship_classes"], 18),
            "filters": filter_terms(chart_data["path_atlas"], ["weakest_status", "bridge_classes", "relationship_classes", "over_six_hops"]),
        },
        {
            "number": 8,
            "title": "Contradiction / Boundary Overlay",
            "filename": "08_contradiction_boundary_overlay.html",
            "description": "Boundary and contradiction markers grouped by record type and status.",
            "csvs": "contradiction_boundary_overlay.csv",
            "chart_html": render_boundary_overlay_svg(chart_data["boundary_rows"]),
            "preview_html": chart_row_table(chart_data["boundary_rows"], ["record_id", "record_type", "status", "claim_type", "boundary_kind", "relationship_class", "summary"], 18),
            "filters": filter_terms(chart_data["boundary_rows"], ["record_type", "status", "boundary_kind", "relationship_class"]),
        },
        {
            "number": 9,
            "title": "Temporal Cluster Swimlanes",
            "filename": "09_temporal_cluster_swimlanes.html",
            "description": "Dated event-link markers placed on one swimlane per cluster.",
            "csvs": "temporal_cluster_swimlanes.csv",
            "chart_html": render_swimlanes_svg(chart_data["swimlanes"]),
            "preview_html": chart_row_table(chart_data["swimlanes"], ["cluster_id", "start_date", "event_id", "event_title", "relationship_class", "status", "source_count"], 18),
            "filters": filter_terms(chart_data["swimlanes"], ["cluster_id", "status", "event_link_status", "relation_type", "relationship_class"]),
        },
        {
            "number": 10,
            "title": "Relationship-Class Treemap",
            "filename": "10_relationship_type_treemap.html",
            "description": "Weighted relationship/event-link buckets grouped by lineage, diffusion, personnel, narrative, contested, and hypothesis classes.",
            "csvs": "relationship_type_treemap.csv",
            "chart_html": render_treemap_svg(chart_data["relation_type_counts"]),
            "preview_html": chart_row_table(chart_data["relation_type_counts"], ["relationship_class", "relation_family", "relation_type", "status", "weighted_count", "row_count"], 18),
            "filters": filter_terms(chart_data["relation_type_counts"], ["relationship_class", "relation_family", "status", "public_scope"]),
        },
        {
            "number": 11,
            "title": "Person-Source Bipartite Graph",
            "filename": "11_person_source_bipartite.html",
            "description": "Top person-source evidence links derived from direct, claim, relationship, event, and event-link paths.",
            "csvs": "person_source_bipartite_nodes.csv / person_source_bipartite_edges.csv",
            "chart_html": render_bipartite_svg(chart_data["person_source_nodes"], chart_data["person_source"]),
            "preview_html": chart_row_table(chart_data["person_source"], ["person_name", "source_id", "source_grade", "contexts"], 18),
            "filters": filter_terms(chart_data["person_source"], ["source_grade", "contexts", "public_evidence_state"]),
        },
        {
            "number": 12,
            "title": "Public Narrative Readiness",
            "filename": "12_public_narrative_readiness.html",
            "description": "Readiness tiers for public narration, with privacy and boundary gates preserved.",
            "csvs": "public_narrative_readiness.csv",
            "chart_html": render_readiness_svg(chart_data["readiness_counts"]),
            "preview_html": chart_row_table(chart_data["readiness_counts"], ["readiness", "count"], 12),
            "filters": filter_terms(chart_data["readiness_counts"], ["readiness"]),
        },
    ], key=lambda spec: int(spec["number"]))
