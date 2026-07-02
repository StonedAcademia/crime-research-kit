# Export Artifacts Runbook

Use this runbook to generate public-safe TRCR exports from a reviewed case. All
commands assume the `tc-c-kit` repository root.

## Preflight

Run validation and public-output checks before export:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-public-export data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-privacy-redactions data/cases/<case_slug> --require-redaction-log
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-source-independence data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py review-narrative-readiness data/cases/<case_slug> --require-spans
```

Default exports include public rows only. Use `--include-private` only for
internal review artifacts that must not be published.

## Evidence Board

Write the Markdown evidence board:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py report data/cases/<case_slug>
```

Output:

```text
data/cases/<case_slug>/exports/evidence_board.md
```

## Manim CSVs

Export public-safe Manim-ready CSVs:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-manim data/cases/<case_slug>
```

Outputs:

```text
data/cases/<case_slug>/exports/manim/sources.csv
data/cases/<case_slug>/exports/manim/people.csv
data/cases/<case_slug>/exports/manim/events.csv
data/cases/<case_slug>/exports/manim/event_links.csv
data/cases/<case_slug>/exports/manim/relationships.csv
data/cases/<case_slug>/exports/manim/claims.csv
data/cases/<case_slug>/exports/manim/places.csv
```

## Cross-Case Timeline

Export the public-safe timeline and claim corroboration index:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-timeline data/cases
```

Outputs:

```text
data/exports/timeline/cases.csv
data/exports/timeline/timeline.csv
data/exports/timeline/corroborations.csv
data/exports/timeline/timeline.md
```

For internal review, opt in explicitly:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-timeline data/cases \
  --include-private \
  --out-dir data/exports/timeline_internal
```

## Case Charts

Export the people graph and subcase timeline charts:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-case-charts data/cases/<case_slug>
```

Outputs:

```text
data/cases/<case_slug>/exports/charts/people_graph.html
data/cases/<case_slug>/exports/charts/people_nodes.csv
data/cases/<case_slug>/exports/charts/people_edges.csv
data/cases/<case_slug>/exports/charts/subcase_timelines.html
data/cases/<case_slug>/exports/charts/subcase_timelines.csv
data/cases/<case_slug>/exports/charts/subcase_summary.csv
```

## People Clusters

Run evidence-weighted Leiden clustering and graph-kernel/KDE analysis:

```bash
uv run --extra dev --with igraph --with leidenalg \
  python .agents/skills/truecrime-cult-research/scripts/tcr.py export-people-clusters data/cases/<case_slug> --include-private
```

This export is typically internal review because graph clustering can surface
weak co-mentions and bridge hypotheses. Treat dashed or weak links as leads,
not public claims.

Outputs:

```text
data/cases/<case_slug>/exports/clusters/people_clusters.html
data/cases/<case_slug>/exports/clusters/people_clusters.csv
data/cases/<case_slug>/exports/clusters/cluster_summary.csv
data/cases/<case_slug>/exports/clusters/people_cluster_edges.csv
data/cases/<case_slug>/exports/clusters/people_kernel_matrix.csv
data/cases/<case_slug>/exports/clusters/clusters.md
```

## Analysis Charts

Build the extended analysis chart package:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-analysis-charts data/cases/<case_slug> --include-private
```

Outputs include:

```text
data/cases/<case_slug>/exports/analysis_charts/analysis_charts.html
data/cases/<case_slug>/exports/analysis_charts/cluster_bridge_sankey_nodes.csv
data/cases/<case_slug>/exports/analysis_charts/cluster_bridge_sankey_links.csv
data/cases/<case_slug>/exports/analysis_charts/evidence_confidence_heatmap.csv
data/cases/<case_slug>/exports/analysis_charts/claim_corroboration_matrix.csv
data/cases/<case_slug>/exports/analysis_charts/source_quality_dashboard.csv
data/cases/<case_slug>/exports/analysis_charts/public_narrative_readiness.csv
```

Use these artifacts for review and readiness decisions. Do not treat chart
structure as evidence unless the underlying ledger rows are source-supported.

## UFB v2 Bundle

Export a public-safe Phanestead-readable UFB v2 bundle:

```bash
bun deployment/scripts/export_trcr_ufb.mjs data/cases/<case_slug> \
  --out data/cases/<case_slug>/exports/ufb/<case_slug>.ufb_v2
```

The exporter lives under `deployment/scripts/` because it is a deployment and
interop artifact. From the `tc-c-kit` root, the default Phanestead checkout path
is `../../phanestead-full`. Override it when needed:

```bash
bun deployment/scripts/export_trcr_ufb.mjs data/cases/<case_slug> \
  --out data/cases/<case_slug>/exports/ufb/<case_slug>.ufb_v2 \
  --phanestead-root /path/to/phanestead-full
```

The exporter also writes companion files beside the bundle:

```text
data/cases/<case_slug>/exports/ufb/<case_slug>.ufb_v2.summary.json
```

Use `--include-private` only for internal testing bundles.
