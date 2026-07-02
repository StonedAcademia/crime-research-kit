# Export Operations

## `exportManim`

Exports public-safe Manim-ready CSVs.

CLI:

```bash
crk-ledger export-manim data/cases/<case_slug>
```

Payload field: `include_private`. Creates CSVs under `exports/manim/` for
sources, people, places, claims, events, event links, and relationships.

## `exportTimeline`

Exports a cross-case timeline and claim corroboration index.

CLI:

```bash
crk-ledger export-timeline data/cases
```

Payload fields: `cases_root`, `out_dir`, and `include_private`. Creates
`cases.csv`, `timeline.csv`, `corroborations.csv`, and `timeline.md`. The
default output path is `data/exports/timeline/`.

## `exportCaseCharts`

Exports case-level chart artifacts for people graph and subcase timeline
review.

CLI:

```bash
crk-ledger export-case-charts data/cases/<case_slug>
```

Payload fields: `out_dir` and `include_private`. Creates
`people_graph.html`, `people_nodes.csv`, `people_edges.csv`,
`subcase_timelines.html`, `subcase_timelines.csv`, and `subcase_summary.csv`.
The default output path is `data/cases/<case_slug>/exports/charts/`.

## `exportAnalysisCharts`

Exports public-readiness, source-quality, corroboration, path, and relationship
analysis artifacts. This is the main source-independence tooling surface.

CLI:

```bash
crk-ledger export-analysis-charts data/cases/<case_slug> --include-private
```

Payload fields: `out_dir`, `clusters_dir`, and `include_private`. Creates:

- `analysis_charts.html`
- `analysis_charts.md`
- Sankey and layered knowledge graph CSVs
- bridge fragility CSVs
- claim corroboration matrix and edges
- source quality dashboard
- evidence confidence heatmap CSVs
- contradiction boundary overlay
- temporal cluster swimlanes
- public narrative readiness
- relationship type treemap
- person-source bipartite CSVs
- six degree path atlas and segments

Use `source_quality_dashboard.csv` and `claim_corroboration_matrix.csv` to
check reliability grades, source counts, independent source counts, and
public-readiness before upgrading claims or exporting public scripts.

## `exportPeopleClusters`

Runs evidence-weighted Leiden clustering and graph-kernel/KDE density analysis
over the people graph.

CLI:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' --with igraph --with leidenalg \
  crk-ledger export-people-clusters data/cases/<case_slug> --include-private
```

Payload fields: `out_dir`, `charts_dir`, `include_private`, `resolution`,
`seed`, and `sigma`. Creates `people_clusters.html`, `people_clusters.csv`,
`cluster_summary.csv`, `people_cluster_edges.csv`, `people_kernel_matrix.csv`,
and `clusters.md`. The default output path is
`data/cases/<case_slug>/exports/clusters/`.
