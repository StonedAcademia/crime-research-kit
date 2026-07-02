"""Markdown manifest writing for analysis chart exports."""

from __future__ import annotations

from typing import Any

from adapters.ops.evidence.reports.analysis.command.context import AnalysisContext


def write_analysis_index(ctx: AnalysisContext, chart_specs: list[dict[str, Any]]) -> None:
    chart_page_lines = [f"- `{spec['filename']}` - {spec['title']}" for spec in chart_specs]
    index = [
        f"# Analysis charts: {ctx.case_title}",
        "",
        f"Scope: {'public and private/internal rows' if ctx.include_private else 'public-export rows only'}",
        "",
        "## Interactive HTML pages",
        "",
        "- `analysis_charts.html` - chart index",
        *chart_page_lines,
        "",
        "## Files",
        "",
        "- `analysis_charts.html`",
        "- `cluster_bridge_sankey.csv`",
        "- `cluster_bridge_sankey_nodes.csv`",
        "- `cluster_bridge_sankey_links.csv`",
        "- `layered_knowledge_graph_nodes.csv`",
        "- `layered_knowledge_graph_edges.csv`",
        "- `layered_knowledge_graph_v2_nodes.csv`",
        "- `layered_knowledge_graph_v2_edges.csv`",
        "- `layered_knowledge_graph_v2_layers.csv`",
        "- `evidence_confidence_heatmap.csv`",
        "- `evidence_confidence_heatmap_aggregate.csv`",
        "- `bridge_fragility.csv`",
        "- `bridge_fragility_segments.csv`",
        "- `claim_corroboration_matrix.csv`",
        "- `claim_corroboration_edges.csv`",
        "- `source_quality_dashboard.csv`",
        "- `sixdof_path_atlas.csv`",
        "- `sixdof_path_segments.csv`",
        "- `contradiction_boundary_overlay.csv`",
        "- `temporal_cluster_swimlanes.csv`",
        "- `relationship_type_treemap.csv`",
        "- `person_source_bipartite.csv`",
        "- `person_source_bipartite_nodes.csv`",
        "- `person_source_bipartite_edges.csv`",
        "- `public_narrative_readiness.csv`",
        "",
        "## Guardrails",
        "",
        "- These charts are evidence-navigation tools, not proof of a unified conspiracy.",
        "- Category bridges remain distinct from direct personal or institutional relationships.",
        "- Relationship classes separate documented succession, method diffusion, personnel bridges, narrative inheritance, contested overlap, and hypotheses requiring more sources.",
        "- Lead-only and boundary rows must remain visible when interpreting PROMIS/Maxwell, Barr/Epstein, and methodology-influence lanes.",
    ]
    (ctx.out / "analysis_charts.md").write_text("\n".join(index) + "\n", encoding="utf-8")
