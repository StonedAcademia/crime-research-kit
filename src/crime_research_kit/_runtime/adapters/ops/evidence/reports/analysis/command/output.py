"""Analysis chart data adapters."""

from __future__ import annotations

from typing import Any


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
