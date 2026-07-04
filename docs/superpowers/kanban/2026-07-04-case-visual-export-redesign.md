# Case Visual Export Redesign Kanban

Spec: `docs/superpowers/specs/2026-07-04-case-visual-export-redesign.md`
Plan: `docs/superpowers/plans/2026-07-04-case-visual-export-redesign.md`

## Board Rules

- Move cards only when work has actually reached the next state.
- No retired public chart command aliases are retained.
- Public-safe defaults and `--include-private` labeling cannot regress.
- Audit CSVs remain traceable even when metadata is hidden from the main chart
  viewport.

## Status Ledger

| ID | Status | Owner | Task | Files | Depends On | Checks | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| VIZ-000 | done | main | Create spec, plan, and kanban docs | `docs/superpowers/{specs,plans,kanban}/2026-07-04-case-visual-export-redesign.md` | - | docs review | Initial planning package created. |
| VIZ-001 | done | main | Add `export-case-visuals` operation contract | CLI, ops wrappers, SDK catalog/request/export, MCP gated tools | VIZ-000 | SDK/catalog/CLI tests | Retired chart commands removed from public surfaces. |
| VIZ-002 | done | main | Build visual package data and audit CSV writer | evidence reports visual package modules | VIZ-001 | integration export tests | Reuses existing ledger/scoring helpers. |
| VIZ-003 | done | main | Bundle D3/Cytoscape frontend runtime | `frontend/*`, committed static assets | VIZ-001 | `moon run crk:frontend-build` | No CDN/runtime web dependency. |
| VIZ-004 | done | main | Render four canonical consoles | visual templates/runtime renderer | VIZ-002,VIZ-003 | renderer + integration tests | Evidence, network, timeline, matrix. |
| VIZ-005 | done | main | Render curated native deck | visual templates/runtime renderer | VIZ-002,VIZ-003 | deck unit + integration tests | Native slide deck, no iframe wrapper. |
| VIZ-006 | done | main | Remove retired docs/tests/artifact references | docs, tests, CLI surface snapshots | VIZ-004,VIZ-005 | docs drift + targeted pytest | No visible generation labels. |
| VIZ-007 | done | main | Visual/privacy review and final gate | generated sample outputs, tests | VIZ-006 | `moon run crk:check && moon run crk:test` | Full gates passed. |

## Done

| Card | Outcome |
| --- | --- |
| VIZ-000 | Planning package created under docs/superpowers. |
| VIZ-001 | `export-case-visuals` wired through CLI, ops, SDK, Skill API catalog, and MCP. |
| VIZ-002 | Visual package builder writes manifest, audit CSVs, deck, explorer, and consoles. |
| VIZ-003 | Frontend bundle includes D3 and Cytoscape with committed static assets. |
| VIZ-004 | Four canonical consoles render from structured JSON payloads. |
| VIZ-005 | Deck renders as native slide sections. |
| VIZ-006 | Docs, tests, and CLI snapshot updated to the replacement export. |
| VIZ-007 | `moon run crk:check` and `moon run crk:test` passed. |

## Blocked / Watch

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Removing retired commands breaks public docs and SDK snapshots | Broad drift failures | Update CLI surface, SDK catalog, docs, and tests in the same slice. |
| D3/Cytoscape bundle size grows committed JS | Build/package bloat | Keep one shared bundle and verify package-data still ships. |
| Dense audit metadata disappears from analyst workflow | Evidence traceability regression | Keep `audit/*.csv` and collapsed evidence/data drawers. |
| Optional clustering dependencies missing | Network console could fail | Use deterministic fallback layout and record manifest warning. |
