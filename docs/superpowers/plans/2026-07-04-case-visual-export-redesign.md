# Case Visual Export Redesign Plan

## Summary

Implement `export-case-visuals` as the single case-visual export operation.
Replace the current chart/deck public contract, consolidate generated visuals
into four canonical consoles, and make the curated slide deck the primary
review artifact. Keep audit CSVs, but move them behind evidence/data drawers
and `audit/` outputs instead of rendering full tables beneath charts.

## Implementation Changes

- Add a new visual package builder under the evidence reports runtime. It
  should reuse the existing ledger reads, public/private filters, analysis
  scoring helpers, and report atomic write helper instead of duplicating IO.
- Add one CLI/SDK/MCP operation named `export-case-visuals` /
  `exports.case_visuals` / `export_case_visuals` / `exportCaseVisuals`.
- Remove retired public chart commands and catalog entries for case charts,
  analysis charts, and people clusters.
- Generate:
  - `deck.html`
  - `explorer.html`
  - four `consoles/*.html` files
  - `audit/*.csv`
  - `manifest.json`
- Update the frontend bundle to include D3 and Cytoscape through NPM/esbuild.
  Generated files must not require network access.
- Use structured JSON payloads for chart marks and inspector details. Do not
  use SVG title strings as the source of interaction truth.
- Collapse dense tables into evidence/data drawers. The default viewport should
  prioritize the chart, key metrics, filters, caveats, and inspector.
- Update runbooks, Skill API docs, operation catalog docs, CLI surface
  snapshots, and tests to the new command and artifact names.

## Task Order

1. Create planning docs and initialize kanban.
2. Add the new operation contract across CLI, ops wrappers, SDK catalog, request
   models, SDK exports, and MCP gated tools.
3. Build the visual package data layer and audit CSV writer.
4. Build the bundled frontend runtime with D3 and Cytoscape.
5. Render the four consoles and curated deck from the shared package.
6. Remove retired command/docs/test references.
7. Verify public/private behavior, HTML self-containment, and visual smoke.

## Acceptance Criteria

- `crk-ledger export-case-visuals data/examples/synthetic_case --out-dir <tmp>`
  writes the full visual package.
- Public mode excludes private records and labels output as public-export rows.
- `--include-private` includes internal rows and labels all HTML as internal
  review.
- `deck.html` is not an iframe wrapper around generated chart pages.
- Console pages render the four canonical surfaces and keep audit tables
  collapsed.
- `manifest.json` lists all generated files and warning states.
- No docs, tests, command names, or visible chart titles use generation labels.
- Old chart export commands are absent from the CLI surface and SDK catalog.

## Test Plan

- Unit:
  - renderer output is self-contained and includes bundled visual JS/CSS.
  - mark payloads serialize expected fields.
  - manifest generation records privacy mode and artifacts.
  - deck output is native sections, not iframe payloads.
- Integration:
  - export the synthetic case in public mode.
  - export the synthetic case with `--include-private`.
  - verify audit CSVs and all HTML artifacts exist.
- SDK/MCP:
  - dry-run SDK export builds the expected `export-case-visuals` command.
  - MCP gated tool maps to `exports.case_visuals`.
  - operation catalog/docs drift tests pass.
- Frontend:
  - `moon run crk:frontend-build`.
  - Playwright smoke when `web-local` is available: deck and consoles have
    nonblank visual roots, working inspector text, and collapsed audit drawers.
- Final:
  - `moon run crk:check`
  - `moon run crk:test`

## Implementation Notes

- Keep modules under the repository shape limits. Add README files for any new
  Python-bearing directories.
- Use path-scoped staging and commits.
- Do not remove dense provenance data; relocate it to audit CSVs and drawers.
- If optional graph clustering libraries are unavailable, relationship network
  falls back to deterministic component/group layout and records a warning in
  `manifest.json`.
