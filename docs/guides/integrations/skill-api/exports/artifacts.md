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

## `exportCaseVisuals`

Exports the curated case visual package: a native HTML deck, visual console
index, four focused console pages, audit CSVs, and a manifest.

CLI:

```bash
crk-ledger export-case-visuals data/cases/<case_slug>
```

Payload fields: `out_dir` and `include_private`. Creates:

- `deck.html`
- `explorer.html`
- `consoles/evidence_readiness.html`
- `consoles/relationship_network.html`
- `consoles/timeline_movement.html`
- `consoles/claim_source_matrix.html`
- `audit/*.csv`
- `manifest.json`

The default output path is `data/cases/<case_slug>/exports/visuals/`.
Internal-review output with `include_private=true` defaults to
`data/cases/<case_slug>/exports/internal/visuals/`.
