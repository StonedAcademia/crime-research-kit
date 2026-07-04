# Export Artifacts Runbook

Use this runbook to generate public-safe CRK exports from a reviewed case. All
commands assume the `tc-c-kit` repository root.

## Preflight

Run validation and public-output checks before export:

```bash
crk-ledger validate data/cases/<case_slug>
crk-ledger audit-public-export data/cases/<case_slug>
crk-ledger audit-privacy-redactions data/cases/<case_slug> --require-redaction-log
crk-ledger audit-source-independence data/cases/<case_slug>
crk-ledger review-narrative-readiness data/cases/<case_slug> --require-spans
```

Default exports include public rows only. Use `--include-private` only for
internal review artifacts that must not be published.

## Evidence Board

Write the Markdown evidence board:

```bash
crk-ledger report data/cases/<case_slug>
```

Output:

```text
data/cases/<case_slug>/exports/evidence_board.md
```

## Manim CSVs

Export public-safe Manim-ready CSVs:

```bash
crk-ledger export-manim data/cases/<case_slug>
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
crk-ledger export-timeline data/cases
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
crk-ledger export-timeline data/cases \
  --include-private \
  --out-dir data/exports/timeline_internal
```

## Case Visual Package

Export the curated case visual package:

```bash
crk-ledger export-case-visuals data/cases/<case_slug>
```

Outputs:

```text
data/cases/<case_slug>/exports/visuals/deck.html
data/cases/<case_slug>/exports/visuals/explorer.html
data/cases/<case_slug>/exports/visuals/consoles/evidence_readiness.html
data/cases/<case_slug>/exports/visuals/consoles/relationship_network.html
data/cases/<case_slug>/exports/visuals/consoles/timeline_movement.html
data/cases/<case_slug>/exports/visuals/consoles/claim_source_matrix.html
data/cases/<case_slug>/exports/visuals/audit/*.csv
data/cases/<case_slug>/exports/visuals/manifest.json
```

The default package is public-safe and keeps dense provenance rows in
`audit/*.csv` plus the console evidence drawers, not below the charts. For
internal review, opt in explicitly:

```bash
crk-ledger export-case-visuals data/cases/<case_slug> --include-private
```

Internal outputs default to
`data/cases/<case_slug>/exports/internal/visuals/`. Treat relationship
clusters, weak links, and path views as review aids only; do not treat visual
structure as evidence unless the underlying ledger rows are source-supported.

## UFB v2 Bundle

Export a public-safe Phanestead-readable UFB v2 bundle:

```bash
bun deployment/scripts/tools/export_crk_ufb.mjs data/cases/<case_slug> \
  --out data/cases/<case_slug>/exports/ufb/<case_slug>.ufb_v2
```

The exporter lives under `deployment/scripts/tools/` because it is a deployment
and interop helper. From the `tc-c-kit` root, the default Phanestead checkout
path is `../../phanestead-full`. Override it when needed:

```bash
bun deployment/scripts/tools/export_crk_ufb.mjs data/cases/<case_slug> \
  --out data/cases/<case_slug>/exports/ufb/<case_slug>.ufb_v2 \
  --phanestead-root /path/to/phanestead-full
```

The exporter also writes companion files beside the bundle:

```text
data/cases/<case_slug>/exports/ufb/<case_slug>.ufb_v2.summary.json
```

Use `--include-private` only for internal testing bundles.
