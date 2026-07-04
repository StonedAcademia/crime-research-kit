# Case Visual Export Redesign Spec

Date: 2026-07-04. Status: approved for implementation.

Companion plan: `docs/superpowers/plans/2026-07-04-case-visual-export-redesign.md`.
Kanban: `docs/superpowers/kanban/2026-07-04-case-visual-export-redesign.md`.

## Goal

Replace the current chart/deck export surface with one case-visual export that
is easier to read, keeps provenance available without burying charts under
metadata tables, and treats the curated slide deck as a first-class artifact.

The replacement must not introduce visible generation labels or competing chart
families. Existing dense CSV evidence products remain available as audit
artifacts, but the visual product is organized around four canonical consoles
and an authored deck.

## Public Interface

One command replaces the retired chart export commands:

```bash
crk-ledger export-case-visuals <case_dir> [--out-dir <path>] [--include-private]
```

Default outputs:

- Public mode: `data/cases/<case>/exports/visuals/`
- Internal mode: `data/cases/<case>/exports/internal/visuals/`

Produced artifacts:

- `deck.html`: curated main slide deck.
- `explorer.html`: index for the visual consoles.
- `consoles/evidence_readiness.html`
- `consoles/relationship_network.html`
- `consoles/timeline_movement.html`
- `consoles/claim_source_matrix.html`
- `audit/*.csv`: dense provenance and audit tables.
- `manifest.json`: artifact list, privacy mode, generated timestamp, warnings.

The SDK, MCP, and Skill API expose the same operation as:

- SDK catalog operation: `exports.case_visuals`
- SDK request model: `ExportCaseVisualsRequest`
- Skill API operation: `exportCaseVisuals`
- MCP tool: `export_case_visuals`

Remove public support for:

- `export-case-charts`
- `export-analysis-charts`
- `export-people-clusters`

No deprecated aliases are kept.

## Visual Product

The canonical consoles are:

1. **Evidence Readiness**: source quality, claim confidence, public-readiness
   state, contradiction and boundary markers.
2. **Relationship Network**: people, organizations, events, sources,
   relationship classes, evidence strength, caveats, and public/private state.
3. **Timeline Movement**: subcase lanes, event timing, event-link context, and
   path/movement clues.
4. **Claim Source Matrix**: claim/source support, independence, contradiction,
   privacy, and public-safety state.

The deck is an authored summary, not an iframe list of every chart. It must
include a cover, safety/public-output gate, top metrics, and slide-scale
summaries of the four canonical consoles.

## Rendering Contract

Generated HTML is self-contained and offline-viewable after build. Web
visualization libraries are bundled by the existing NPM frontend build, not
loaded from CDN at runtime:

- `d3` powers readiness, timeline, and matrix visuals.
- `cytoscape` powers the relationship network.

Structured mark payloads are the interaction contract:

- `mark_id`
- `mark_type`
- `label`
- `record_ids`
- `source_ids`
- `status`
- `confidence`
- `readiness`
- `summary`
- `caveat`
- `filter_terms`

Inspector, filtering, highlighting, and evidence drawers use this structured
data. SVG `<title>` text is an accessibility fallback, not the application data
source.

## Safety Rules

Public exports remain public-safe by default. `--include-private` is internal
review only and must be clearly labeled in every generated HTML artifact.

Visual text must not imply guilt, cult membership, criminal responsibility,
intent, or hidden control from proximity. Edges and co-occurrence links must
carry caveats when they are contextual, lead-only, disputed, private, or
single-source.
