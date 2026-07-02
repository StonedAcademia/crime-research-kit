"""Static assets and file inventory for analysis chart pages."""

from __future__ import annotations


def analysis_chart_files() -> list[tuple[str, str]]:
    return [
        ("Cluster Bridge Sankey", "cluster_bridge_sankey_nodes.csv / cluster_bridge_sankey_links.csv"),
        ("Layered Knowledge Graph", "layered_knowledge_graph_nodes.csv / layered_knowledge_graph_edges.csv"),
        ("Layered Knowledge Graph v2", "layered_knowledge_graph_v2_nodes.csv / layered_knowledge_graph_v2_edges.csv / layered_knowledge_graph_v2_layers.csv"),
        ("Evidence Confidence Heatmap", "evidence_confidence_heatmap.csv / evidence_confidence_heatmap_aggregate.csv"),
        ("Bridge Fragility", "bridge_fragility.csv / bridge_fragility_segments.csv"),
        ("Claim Corroboration Matrix", "claim_corroboration_matrix.csv / claim_corroboration_edges.csv"),
        ("Source Quality Dashboard", "source_quality_dashboard.csv"),
        ("6DOF Path Atlas", "sixdof_path_atlas.csv / sixdof_path_segments.csv"),
        ("Contradiction / Boundary Overlay", "contradiction_boundary_overlay.csv"),
        ("Temporal Cluster Swimlanes", "temporal_cluster_swimlanes.csv"),
        ("Relationship-Class Treemap", "relationship_type_treemap.csv"),
        ("Person-Source Bipartite Graph", "person_source_bipartite_nodes.csv / person_source_bipartite_edges.csv"),
        ("Public Narrative Readiness", "public_narrative_readiness.csv"),
    ]


def analysis_chart_css() -> str:
    return """
<style>
:root { color-scheme: light; --ink:#182026; --muted:#5d6975; --line:#d9e1e8; --panel:#f8fafc; --accent:#2b6cb0; --good:#237a57; --warn:#b7791f; --bad:#a63a3a; --soft:#eef4fa; }
body { margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color:var(--ink); background:#fff; }
header { padding:28px 36px 18px; border-bottom:1px solid var(--line); background:var(--panel); }
main { padding:24px 36px 56px; max-width:1440px; margin:0 auto; }
h1 { margin:0 0 8px; font-size:26px; letter-spacing:0; }
h2 { margin:0 0 10px; font-size:19px; letter-spacing:0; }
h3 { margin:18px 0 8px; font-size:14px; letter-spacing:0; }
p, li { color:var(--muted); line-height:1.45; }
a { color:var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; }
.grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap:18px; align-items:stretch; }
section, .card { border:1px solid var(--line); border-radius:8px; padding:16px; background:#fff; overflow:hidden; }
.card { display:flex; flex-direction:column; min-height:160px; }
.card-link { margin-top:auto; font-weight:700; }
.wide { grid-column:1 / -1; }
.muted { color:var(--muted); font-size:13px; }
.toolbar { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:16px 0; }
.toolbar input { min-width:260px; flex:1; border:1px solid var(--line); border-radius:6px; padding:9px 10px; font:inherit; }
.toolbar button, .back-link { border:1px solid var(--line); border-radius:6px; background:#fff; color:#283542; padding:8px 10px; font:inherit; font-size:12px; cursor:pointer; }
.toolbar button:hover, .toolbar button[aria-pressed="true"] { background:var(--soft); border-color:#a9bdcf; }
.chart-layout { display:grid; grid-template-columns:minmax(0, 1fr) 320px; gap:16px; align-items:start; }
.inspector { border:1px solid var(--line); border-radius:8px; padding:14px; background:#fbfdff; position:sticky; top:16px; min-height:160px; }
.inspector-title { margin:0 0 8px; font-size:13px; font-weight:800; }
.inspector-body { color:var(--muted); font-size:13px; line-height:1.45; overflow-wrap:anywhere; }
.table-wrap { overflow:auto; border:1px solid var(--line); border-radius:6px; }
table { border-collapse:collapse; width:100%; min-width:720px; font-size:12px; }
th, td { padding:7px 8px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
th { background:var(--soft); color:#24313d; position:sticky; top:0; }
code { background:#edf2f7; padding:1px 4px; border-radius:4px; }
.chart-shell { width:100%; overflow:hidden; border:1px solid var(--line); border-radius:8px; background:#fff; margin:8px 0 12px; }
.chart-shell.scroll-x { overflow-x:auto; }
.chart-svg { display:block; width:100%; height:auto; min-height:240px; }
.chart-bg { fill:#fbfdff; }
.axis { stroke:#93a4b4; stroke-width:1.2; }
.axis-label { fill:#465461; font-size:12px; font-weight:650; }
.node-label { fill:#1f2933; font-size:12px; font-weight:650; }
.mini-label { fill:#53616f; font-size:10.5px; }
.heat-label { fill:#111827; font-size:11px; font-weight:700; }
.warn-label { fill:var(--bad); font-size:11px; font-weight:800; }
.metric { fill:#16202a; font-size:27px; font-weight:800; }
.node-box { fill:#fff; stroke:#bac8d6; stroke-width:1.2; }
.treemap-label { fill:#111827; font-size:10px; font-weight:700; pointer-events:none; }
.data-preview { margin-top:14px; }
.data-preview summary { cursor:pointer; color:var(--muted); font-size:12px; font-weight:700; }
.interactive-mark { cursor:pointer; outline:none; transform-box:fill-box; transform-origin:center; transition:opacity .16s ease, filter .16s ease, stroke-width .16s ease, transform .16s ease; }
.interactive-mark:hover, .interactive-mark:focus { filter:drop-shadow(0 0 5px rgba(43,108,176,.62)); transform:scale(1.035); }
.interactive-mark.is-selected { filter:drop-shadow(0 0 9px rgba(35,122,87,.78)); opacity:1 !important; stroke:#111827 !important; stroke-width:2.4 !important; transform:scale(1.07); animation:selectedPulse 1.25s ease-in-out infinite; }
.interactive-mark.is-related { filter:drop-shadow(0 0 5px rgba(183,121,31,.45)); opacity:.82 !important; }
.interactive-mark.is-dim { opacity:.1 !important; filter:grayscale(.85); }
.inspector.is-live { border-color:#9fb8ce; box-shadow:0 8px 24px rgba(35,52,68,.08); }
.inspector.is-selected { border-color:#88b4a1; box-shadow:0 10px 28px rgba(35,122,87,.12); }
.chart-tooltip { position:fixed; z-index:20; max-width:360px; pointer-events:none; background:#17212b; color:#fff; border-radius:7px; padding:8px 10px; font-size:12px; line-height:1.35; box-shadow:0 10px 26px rgba(10,22,34,.24); opacity:0; transform:translate(10px, 12px); transition:opacity .12s ease, transform .12s ease; overflow-wrap:anywhere; }
.chart-tooltip.is-visible { opacity:.96; transform:translate(12px, 14px); }
.click-flash { position:fixed; z-index:19; width:10px; height:10px; border-radius:999px; pointer-events:none; border:2px solid rgba(43,108,176,.55); transform:translate(-50%, -50%) scale(1); animation:clickFlash .48s ease-out forwards; }
@keyframes selectedPulse { 0%, 100% { filter:drop-shadow(0 0 7px rgba(35,122,87,.55)); } 50% { filter:drop-shadow(0 0 13px rgba(35,122,87,.9)); } }
@keyframes clickFlash { to { opacity:0; transform:translate(-50%, -50%) scale(9); } }
@media (prefers-reduced-motion: reduce) { .interactive-mark, .chart-tooltip, .click-flash { transition:none; animation:none; } .interactive-mark:hover, .interactive-mark:focus, .interactive-mark.is-selected { transform:none; } }
@media (max-width: 900px) { header, main { padding-left:18px; padding-right:18px; } .chart-layout { grid-template-columns:1fr; } .inspector { position:static; } }
</style>
"""
