# Export Operations

## `exportTimeline`

Exports a cross-case timeline and claim corroboration index.

CLI:

```bash
crk-ledger export-timeline data/cases
```

Payload fields: `cases_root`, `out_dir`, and `include_private`. Creates
`cases.csv`, `timeline.csv`, `corroborations.csv`, and `timeline.md`. The
default output path is `data/exports/internal/timeline/` for a cases root or
`exports/internal/timeline/` for a single case workspace.

## `exportCaseVisuals`

Exports the curated case visual package: a visual console index, focused
console pages, audit CSVs, static assets, and a manifest.

CLI:

```bash
crk-ledger export-case-visuals data/cases/<case_slug>
```

Payload fields: `out_dir` and `include_private`. Creates:

- `index.html`
- `consoles/evidence_readiness.html`
- `consoles/cluster_overview.html`
- `consoles/cluster_detail.html`
- `consoles/source_subproject.html`
- `consoles/relationship_network.html`
- `consoles/timeline_movement.html`
- `consoles/claim_source_matrix.html`
- `data/*.js`
- `static/*`
- `audit/*.csv`
- `manifest.json`

The default output path is `data/cases/<case_slug>/exports/internal/visuals/`.
Set `include_private=true` only for internal review output.
