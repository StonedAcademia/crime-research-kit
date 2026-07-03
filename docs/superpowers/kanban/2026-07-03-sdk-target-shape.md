# SDK Target Shape Kanban

Spec: `docs/superpowers/specs/2026-07-03-sdk-target-shape.md`
Plan: `docs/superpowers/plans/2026-07-03-sdk-target-shape.md`

## Board Rules

- Move one card at a time from Ready to In Progress.
- Every implementation card gets tests or an explicit no-code reason.
- No card may add `case_builder.*` compatibility aliases.
- No card may advertise top-level `adapters`, `core`, or `pipeline` as public
  SDK imports.
- Safety defaults cannot regress: public-safe reads/exports, staged automated
  writes, gated canonical import.

## Status Ledger

| Card | Status | Owner | Depends on | Owned files/modules | Notes |
| --- | --- | --- | --- | --- | --- |
| SDK-000 Inventory and planning package | done | main | - | `docs/superpowers/{specs,plans,kanban}/2026-07-03-sdk-target-shape.md` | Planning package created. |
| SDK-001 Freeze operation inventory | done | main | SDK-000 | `docs/superpowers/inventories/2026-07-03-sdk-operation-inventory.md`, SDK spec/plan/kanban | Inventory reconciles CLI, MCP, ops, workflow, Skill API docs, and SDK/not-SDK disposition. |
| SDK-002 Decide public namespace | done | main | SDK-001 | SDK spec/plan/kanban | `crime_research_kit.sdk` recorded as the public import surface; no legacy aliases. |
| SDK-003 Add SDK package skeleton | done | worker-sdk-skeleton + main integration | SDK-002 | `src/crime_research_kit/**`, SDK import tests, `pyproject.toml` package discovery, built-package import smoke | SDK skeleton, package discovery, semver, changelog, and import checks landed. |
| SDK-004 Define public result/error types | done | worker-sdk-results + main integration | SDK-003 | `src/crime_research_kit/sdk/results.py`, `src/crime_research_kit/sdk/errors.py`, result/error tests | Public result/error types landed and are exported from `crime_research_kit.sdk`. |
| SDK-005 Define `OperationSpec` catalog | done | main | SDK-004 | `src/crime_research_kit/sdk/operations.py`, operation catalog tests | Metadata-only catalog landed from the operation inventory. |
| SDK-006 Add catalog parity tests | done | main | SDK-005 | catalog parity tests | CLI commands and MCP tools are checked against catalog mappings. |
| SDK-007 Build `CrkContext` | done | main | SDK-005 | `src/crime_research_kit/sdk/context.py`, context tests | Context now owns roots, settings, privacy defaults, and transport selection. |
| SDK-008 Build `CrkClient` and `CaseClient` | done | main | SDK-005, SDK-007 | SDK client modules and tests | Thin client and case handles landed without operation wrappers. |
| SDK-009 Wrap case and record reads | done | main | SDK-005, SDK-008 | SDK case/record modules and tests | Public-safe case info, case listing, record reads, and source-text reads landed. |
| SDK-010 Wrap source operations | done | main | SDK-005, SDK-008 | SDK source modules and tests | Source add, ingest, preserve, discover, parse, and OCR wrappers landed with dependency errors. |
| SDK-011 Wrap extraction operations | done | main | SDK-005, SDK-008 | SDK extraction modules and tests | Draft/list/read/save/import_reviewed/ner_suggest wrappers landed with explicit import approval. |
| SDK-012 Wrap review operations | done | main | SDK-005, SDK-008 | SDK review modules and tests | Validation, dedupe, identity, contradiction, readiness, privacy, public-export, and source-independence wrappers landed. |
| SDK-013 Wrap export operations | done | main | SDK-005, SDK-008 | SDK export modules and tests | Public-safe export wrappers landed. |
| SDK-014 Add workflow facade | done | main | SDK-005, SDK-008 | `src/crime_research_kit/sdk/workflows.py`, `src/pipeline/app/service.py`, workflow tests | Workflow facade landed without public graph-node imports. |
| SDK-015 Repoint CLI handlers | done | main | SDK-006, SDK-009 to SDK-014 | `src/adapters/interfaces/cli/**`, CLI tests | `cr-kit` handlers now route through SDK facades without command surface changes. |
| SDK-016 Repoint MCP tools | done | main | SDK-006, SDK-009 to SDK-014 | `src/adapters/interfaces/mcp/**`, MCP tests | SDK-backed MCP tools now route through SDK facades while preserving MCP payload compatibility; `run_report` remains direct pending evidence-board privacy semantics. |
| SDK-017 Generate or drift-check Skill API docs | done | worker-sdk-docs-drift + main integration | SDK-005 | docs drift tests, Skill API docs | Skill API operation docs now drift-check against the SDK catalog. |
| SDK-018 Define private runtime policy | done | main | SDK-006, SDK-015, SDK-016 | packaging docs/tests | Public docs declare only `crime_research_kit.sdk`; top-level runtime packages are private pre-1.0 internals. |
| SDK-019 Update architecture docs | done | main | SDK-018 | architecture docs | System overview and workflow docs now show SDK as the public Python layer and CLI/MCP as adapters. |
| SDK-020 Release-note and gate pass | done | main | SDK-019 | `CHANGELOG.md`, release/gate checks | Final full-series gate passed with `moon run crk:test`. |
| SDK-021 Future HTTP route binding | review | main + workers | SDK-005 | catalog metadata only | Catalog-driven HTTP route metadata implemented; reviewer checking no-server boundary. |
| SDK-022 Move internals under `_runtime` | backlog | unassigned | SDK-018 | `_runtime` migration if chosen | Backlog; runtime modules are documented private for now. |
| SDK-023 SDK examples package | done | main | SDK-014 | SDK examples/docs | Packaged SDK examples and docs landed. |
| SDK-024 Catalog-driven MCP registration | done | main + workers | SDK-006, SDK-016 | MCP registration code/tests/docs | Catalog-backed MCP registration metadata landed; prompts/resources remain explicit. |
| SDK-025 Strict request models | done | main + workers | SDK-005 | request models/tests/docs | Strict request models landed for catalog `request_model` names. |

Dependency note: SDK-015, SDK-016, SDK-018, SDK-019, and SDK-020 are done.
SDK-015, SDK-016, SDK-018, SDK-019, SDK-020, SDK-023, and SDK-024 are done.
SDK-025 is done. SDK-021 and SDK-022 remain backlog follow-up slices.

## Done

| Card | Outcome |
| --- | --- |
| SDK-000 Inventory and planning package | Deep inventory, target-shape spec, execution plan, and kanban created. |
| SDK-001 Freeze operation inventory | Live operation inventory added under `docs/superpowers/inventories/`. |
| SDK-002 Decide public namespace | Public namespace recorded as `crime_research_kit.sdk`; no legacy aliases. |
| SDK-003 Add SDK package skeleton | Public package skeleton, README coverage, package discovery, and import tests landed. |
| SDK-004 Define public result/error types | `OperationResult`, warnings, error details, error codes, and SDK exceptions landed. |
| SDK-005 Define `OperationSpec` catalog | Metadata-only operation catalog landed with safety tiers and adapter mappings. |
| SDK-006 Add catalog parity tests | CLI command and MCP tool surfaces are checked against catalog entries. |
| SDK-007 Build `CrkContext` | Context owns roots, settings, privacy defaults, and transport mode without runtime imports. |
| SDK-008 Build `CrkClient` and `CaseClient` | Thin SDK entrypoint and case-scoped handle landed; operation wrappers remain separate cards. |
| SDK-009 Wrap case and record reads | Public-safe case info, case listing, record reads, and source-text reads now return `OperationResult`. |
| SDK-010 Wrap source operations | Source add, ingest, preserve, discover, parse, and OCR wrappers now return SDK results with actionable optional failures. |
| SDK-011 Wrap extraction operations | Extraction draft, list, read, save, reviewed import, and NER suggestion wrappers now return SDK results with explicit import approval. |
| SDK-012 Wrap review operations | Validation, duplicate review, identity review, contradiction audits, narrative readiness, privacy redaction audits, public export audits, and source-independence audits now return SDK results. |
| SDK-013 Wrap export operations | Manim, case-chart, analysis-chart, people-cluster, and cross-case timeline exports now return SDK results with public-safe defaults. |
| SDK-014 Add workflow facade | Case-builder plan and resume workflows now return SDK results through `client.workflows` without public graph-node imports. |
| SDK-015 Repoint CLI handlers | `cr-kit` workflow, discovery, parse, and OCR handlers now call SDK facades while preserving command names, flags, and JSON payload shape. |
| SDK-016 Repoint MCP tools | SDK-backed MCP read, retrieval, staged-write, gated import, and public export tools now call SDK facades while preserving MCP command diagnostics, string errors, legacy result names, and privacy-note payloads. `run_report` remains direct pending evidence-board privacy semantics. |
| SDK-017 Generate or drift-check Skill API docs | Skill API operation docs now drift-check names, safety tiers, and result envelope against the SDK catalog. |
| SDK-018 Define private runtime policy | Public docs now declare `crime_research_kit.sdk` as the only public Python SDK import surface, top-level runtime packages are documented private, and governance tests prevent public docs from advertising runtime imports. |
| SDK-019 Update architecture docs | Architecture docs now describe `crime_research_kit.sdk` as the public Python layer, CLI/MCP as adapters, and top-level runtime packages as private implementation. |
| SDK-020 Release-note and gate pass | Developer SDK quick start, catalog reference drift-gate docs, release metadata, shape-governance budgets, `moon run crk:check`, and final `moon run crk:test` gate completed. |
| SDK-023 SDK examples package | Packaged SDK example recipes now cover case info, source ingest dry-run, packet review, public-safe export planning, and workflow resume decisions. |
| SDK-024 Catalog-driven MCP registration | SDK-backed MCP tool registration metadata is catalog-derived where safe; `run_report`, prompts, and resources remain explicit MCP content. |
| SDK-025 Strict request models | Catalog `request_model` names now resolve to strict pydantic request models under `crime_research_kit.sdk.requests`. |

## In Progress

| Card | Owner | Notes |
| --- | --- | --- |
| None | - | No cards currently in progress. |

## Review

| Card | Owner | Notes |
| --- | --- | --- |
| SDK-021 | reviewer | Catalog-driven HTTP route metadata; no HTTP server. |

## Claimed

| Card | Owner | Notes |
| --- | --- | --- |
| None | - | No unstarted cards are claimed. |

## Ready

| Card | Priority | Depends on | Acceptance |
| --- | --- | --- | --- |
| None | - | No cards currently ready. |

## Blocked / Dependency-Gated

| Card | Priority | Depends on | Acceptance |
| --- | --- | --- | --- |
| None | - | No cards currently blocked. |

## Backlog

| Card | Priority | Depends on | Acceptance |
| --- | --- | --- | --- |
| SDK-022 Move internals under `_runtime` | P3 | SDK-018 | Top-level implementation packages stop being packaged after console scripts and imports migrate. |

## Blocked / Watch

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Existing worktree has unrelated docs/test changes | SDK docs or implementation could sweep in unrelated work. | Always inspect `git status --short --branch`; stage only SDK paths. |
| Historical plans still mention `src/case_builder` | Agents may implement stale paths. | New spec and plan explicitly target live top-level `src/`; archive old paths. |
| `OpResult` differs from Skill API docs | SDK could stabilize the wrong envelope. | SDK-004 and SDK-017 must align result/docs before adapters are repointed. |
| Subprocess runner leaks into SDK | Public API becomes a CLI wrapper instead of an SDK. | Transport stays private; SDK methods expose operations, not commands. |
| Optional extras become required by accident | Base install gets heavier and less local-friendly. | Packaging policy tests remain in the gate; optional methods raise dependency errors. |
| Evidence-board report lacks public/private switch | Wrapping `reports.evidence_board` as-is could violate public-safe SDK defaults. | Do not expose through SDK until the app-layer report has explicit filtering semantics. |
| `crk-ledger` recursion risk | Current SDK ledger wrappers shell through `crk-ledger`, so repointing `crk-ledger` commands through them would recurse in real execution. | Keep ledger commands direct until a direct SDK transport lands; `cr-kit` handlers are SDK-backed first. |
