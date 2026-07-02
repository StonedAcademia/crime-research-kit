"""Output writing for analysis chart exports."""

from __future__ import annotations

from typing import Any

from adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from adapters.ops.evidence.reports.analysis.command.manifest import write_analysis_index
from adapters.ops.evidence.reports.analysis.pages.render import render_analysis_chart_page, render_analysis_dashboard
from adapters.ops.evidence.reports.analysis.pages.specs import build_analysis_chart_specs
from adapters.ops.evidence.shared.records import write_csv


def write_analysis_outputs(ctx: AnalysisContext, products: dict[str, Any]) -> None:
    out = ctx.out
    write_csv(out / "cluster_bridge_sankey_nodes.csv", products["sankey_nodes"], [
        "cluster_id", "cluster_label", "member_entity_ids", "member_names", "size", "mean_kde_density",
        "internal_edge_weight", "boundary_edge_weight", "notes",
    ])
    write_csv(out / "cluster_bridge_sankey_links.csv", products["cluster_bridge_links"], [
        "bridge_id", "src_cluster", "dst_cluster", "src_cluster_label", "dst_cluster_label", "bridge_class", "relationship_classes", "hops",
        "path", "statuses", "source_ids", "claim_ids", "boundary_claim_ids", "boundary_text", "source_grade_counts",
        "public_readiness", "public_export", "notes",
    ])
    write_csv(out / "cluster_bridge_sankey.csv", products["cluster_bridge_rows"], [
        "bridge_id", "src_cluster", "dst_cluster", "bridge_class", "relationship_classes", "hops", "path", "statuses", "source_ids",
        "claim_ids", "boundary_claim_ids", "boundary_text", "public_readiness", "public_export",
    ])
    write_csv(out / "layered_knowledge_graph_nodes.csv", products["layered_nodes"], [
        "node_id", "label", "layer", "cluster_id", "status", "source_count", "public_export",
    ])
    write_csv(out / "layered_knowledge_graph_edges.csv", products["layered_edges"], [
        "src_id", "dst_id", "src_label", "dst_label", "edge_type", "relation_type", "relationship_class", "status", "confidence", "source_count", "source_ids", "claim_ids", "public_export",
    ])
    write_csv(out / "layered_knowledge_graph_v2_nodes.csv", products["layered_v2_nodes"], [
        "node_id", "label", "layer", "layer_order", "cluster_id", "status", "degree", "source_count",
        "independent_source_count", "best_source_grade", "source_grade_counts", "claim_count", "evidence_state",
        "readiness", "boundary_flag", "public_export", "caveat",
    ])
    write_csv(out / "layered_knowledge_graph_v2_edges.csv", products["layered_v2_edges"], [
        "edge_id", "src_id", "dst_id", "src_label", "dst_label", "src_layer", "dst_layer", "edge_type",
        "relation_type", "relationship_class", "relation_family", "bridge_class", "status", "confidence",
        "evidence_weight", "source_count", "independent_source_count", "best_source_grade", "source_grade_counts",
        "claim_ids", "source_ids", "boundary_claim_ids", "readiness", "boundary_flag", "public_export", "caveat",
    ])
    write_csv(out / "layered_knowledge_graph_v2_layers.csv", products["layered_v2_layers"], [
        "layer", "layer_order", "node_count", "public_node_count", "internal_node_count", "candidate_node_count",
        "source_count", "edge_count", "public_edge_count", "lead_or_disputed_edge_count", "public_ready_edge_count",
        "dominant_statuses", "dominant_relationship_classes",
    ])
    write_csv(out / "evidence_confidence_heatmap.csv", products["claim_heatmap"], [
        "claim_id", "claim", "claim_type", "status", "confidence", "status_score", "source_count", "independent_source_count",
        "best_source_grade", "source_grade_counts", "source_grade_score", "privacy_review", "public_export", "boundary_flag", "readiness",
    ])
    write_csv(out / "evidence_confidence_heatmap_aggregate.csv", products["heatmap_aggregate"], [
        "claim_type", "status", "claim_count", "public_claim_count", "internal_only_count", "needs_review_count",
        "avg_confidence", "avg_source_count", "source_count_total", "a_sources", "b_sources", "c_sources", "d_sources",
        "boundary_claim_count", "claim_ids",
    ])
    _write_middle_csvs(ctx, products)
    _write_final_csvs(ctx, products)
    chart_specs = build_analysis_chart_specs(_chart_data(products))
    _write_chart_pages(ctx, chart_specs)
    write_analysis_index(ctx, chart_specs)
    print(f"Exported analysis charts to {out}")


def _write_middle_csvs(ctx: AnalysisContext, products: dict[str, Any]) -> None:
    out = ctx.out
    write_csv(out / "bridge_fragility.csv", products["fragility"], [
        "record_id", "edge_type", "relation_type", "relationship_class", "status", "load_bearing_score", "bridge_class", "source_ids",
        "claim_ids", "support_score", "fragility_score", "fragility_tier", "required_caveat", "example_path",
    ])
    write_csv(out / "bridge_fragility_segments.csv", products["bridge_segment_rows"], [
        "bridge_id", "segment_index", "src_id", "src_label", "dst_id", "dst_label", "record_type", "record_id",
        "relation_type", "relationship_class", "status", "confidence", "source_ids", "claim_ids", "public_export", "guardrail_note",
    ])
    write_csv(out / "claim_corroboration_matrix.csv", products["claim_matrix"], [
        "claim_id", "claim_label", "source_id", "source_title", "source_grade", "source_type", "source_publisher",
        "claim_status", "claim_confidence", "claim_type", "source_role", "safe_public_cell", "boundary_flag",
        "contradiction_flag", "contradicts", "supports",
    ])
    write_csv(out / "claim_corroboration_edges.csv", products["claim_edge_rows"], [
        "from_claim_id", "to_claim_id", "edge_type", "from_claim_status", "to_claim_status", "from_confidence",
        "to_confidence", "shared_source_count", "from_source_ids", "to_source_ids", "boundary_flag", "safe_public_pair",
    ])
    write_csv(out / "source_quality_dashboard.csv", products["source_dashboard"], [
        "source_id", "title", "reliability_grade", "source_type", "publisher", "date_published", "date_accessed", "url",
        "independence_group", "claim_count", "event_count", "event_link_count", "relationship_count", "entity_count",
        "person_count", "verified_claim_count", "corroborated_claim_count", "single_source_claim_count",
        "disputed_claim_count", "unverified_claim_count", "needs_privacy_review_count", "nonpublic_record_count",
        "source_quality_notes", "public_export",
    ])
    write_csv(out / "sixdof_path_atlas.csv", products["path_atlas"], [
        "path_id", "anchor_person", "target_person", "target_entity_id", "target_cluster", "hops", "over_six_hops",
        "path", "weakest_status", "bridge_classes", "relationship_classes", "source_ids", "claim_ids", "caveat",
    ])
    write_csv(out / "sixdof_path_segments.csv", products["path_segments"], [
        "path_id", "segment_index", "src_id", "src_label", "dst_id", "dst_label", "src_cluster", "dst_cluster",
        "record_type", "record_id", "relation_type", "relationship_class", "segment_status", "segment_confidence", "segment_public_export",
        "source_ids", "claim_ids", "is_category_bridge", "is_context_only", "caveat",
    ])


def _write_final_csvs(ctx: AnalysisContext, products: dict[str, Any]) -> None:
    out = ctx.out
    write_csv(out / "contradiction_boundary_overlay.csv", products["boundary_rows"], [
        "record_id", "record_type", "status", "claim_type", "boundary_kind", "relationship_class", "summary", "source_ids", "contradicts",
    ])
    write_csv(out / "temporal_cluster_swimlanes.csv", products["swimlanes"], [
        "cluster_id", "cluster_label", "entity_id", "name", "start_date", "end_date", "date_precision", "event_id",
        "event_title", "event_type", "status", "confidence", "event_link_id", "relation_type", "relationship_class", "event_link_status",
        "event_link_confidence", "source_count", "claim_ids", "source_ids", "is_public_safe", "caveat",
    ])
    write_csv(out / "relationship_type_treemap.csv", products["relation_type_counts"], [
        "record_kind", "relationship_class", "relationship_class_label", "relation_family", "relation_type", "status", "public_scope", "row_count", "weighted_count",
        "source_count", "claim_count", "boundary_count", "lead_only_count", "sample_record_ids",
    ])
    write_csv(out / "person_source_bipartite.csv", products["person_source"], [
        "edge_id", "person_id", "person_name", "cluster_id", "source_id", "source_title", "source_grade", "source_type",
        "publisher", "contexts", "public_evidence_state", "privacy_flag", "notes",
    ])
    write_csv(out / "person_source_bipartite_nodes.csv", products["person_source_nodes"], [
        "node_id", "node_type", "label", "source_id", "entity_id", "reliability_grade", "source_type", "publisher",
        "privacy_level", "living_status", "role_tags", "status", "public_export", "degree",
    ])
    write_csv(out / "person_source_bipartite_edges.csv", products["person_source"], [
        "edge_id", "source_id", "person_id", "source_grade", "source_type", "contexts", "public_evidence_state",
        "privacy_flag", "notes",
    ])
    write_csv(out / "public_narrative_readiness.csv", products["readiness_rows"], [
        "record_type", "record_id", "status", "confidence", "source_count", "best_source_grade", "source_grade_counts",
        "public_export", "privacy_review", "readiness", "boundary_flag", "required_caveat", "relationship_class", "summary",
    ])


def _chart_data(products: dict[str, Any]) -> dict[str, Any]:
    return {
        "sankey_nodes": products["sankey_nodes"],
        "cluster_bridge_links": products["cluster_bridge_links"],
        "cluster_bridges": products["cluster_bridge_rows"],
        "layered_nodes": products["layered_nodes"],
        "layered_edges": products["layered_edges"],
        "layered_v2_nodes": products["layered_v2_nodes"],
        "layered_v2_edges": products["layered_v2_edges"],
        "layered_v2_layers": products["layered_v2_layers"],
        "claim_heatmap": products["claim_heatmap"],
        "heatmap_aggregate": products["heatmap_aggregate"],
        "fragility": products["fragility"],
        "claim_matrix": products["claim_matrix"],
        "source_grade_counts": products["source_grade_count_rows"],
        "source_dashboard": products["source_dashboard"],
        "path_atlas": products["path_atlas"],
        "boundary_rows": products["boundary_rows"],
        "swimlanes": products["swimlanes"],
        "relation_type_counts": products["relation_type_counts"],
        "person_source": products["person_source"],
        "person_source_nodes": products["person_source_nodes"],
        "readiness_counts": products["readiness_counts"],
    }


def _write_chart_pages(ctx: AnalysisContext, chart_specs: list[dict[str, Any]]) -> None:
    for spec in chart_specs:
        (ctx.out / str(spec["filename"])).write_text(
            render_analysis_chart_page(ctx.case_title, ctx.include_private, spec),
            encoding="utf-8",
        )
    (ctx.out / "analysis_charts.html").write_text(
        render_analysis_dashboard(ctx.case_title, ctx.include_private, chart_specs),
        encoding="utf-8",
    )
