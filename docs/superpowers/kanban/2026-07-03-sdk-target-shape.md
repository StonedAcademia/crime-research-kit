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
| SDK-001 Freeze operation inventory | in_progress | main | SDK-000 | `docs/superpowers/inventories/2026-07-03-sdk-operation-inventory.md`, SDK spec/plan/kanban | Critical path. Inventory must reconcile CLI, MCP, ops, workflow, and Skill API docs. |
| SDK-002 Decide public namespace | claimed | main | SDK-001 | SDK spec/plan/kanban | Record `crime_research_kit.sdk` as the public import surface; no legacy aliases. |
| SDK-003 Add SDK package skeleton | claimed | worker-sdk-skeleton | SDK-002 | `src/crime_research_kit/__init__.py`, `src/crime_research_kit/README.md`, `src/crime_research_kit/sdk/__init__.py`, `src/crime_research_kit/sdk/README.md`, `src/crime_research_kit/sdk/context.py`, `src/crime_research_kit/sdk/operations.py`, SDK import tests | Non-overlapping worker slice. Worker must not edit release metadata or unrelated files. |
| SDK-004 Define public result/error types | claimed | worker-sdk-results | SDK-003 | `src/crime_research_kit/sdk/results.py`, `src/crime_research_kit/sdk/errors.py`, result/error tests | Non-overlapping worker slice. Worker must not edit SDK package `__init__` files unless asked during integration. |
| SDK-005 Define `OperationSpec` catalog | ready | unassigned | SDK-004 | `src/crime_research_kit/sdk/operations.py`, operation catalog tests | Next P0 implementation slice after result/error types land. |
| SDK-006 Add catalog parity tests | ready | unassigned | SDK-005 | catalog parity tests, docs drift tests | Depends on catalog shape. |
| SDK-007 Build `CrkContext` | ready | unassigned | SDK-004 | `src/crime_research_kit/sdk/context.py`, context tests | Can proceed after public result/error contracts stabilize. |
| SDK-008 Build `CrkClient` and `CaseClient` | ready | unassigned | SDK-007 | SDK client modules and tests | Blocks case/source/extraction/review/export/workflow wrappers. |
| SDK-009 Wrap case and record reads | ready | unassigned | SDK-008 | SDK case/record modules and tests | Must preserve public-safe defaults. |
| SDK-010 Wrap source operations | ready | unassigned | SDK-008 | SDK source modules and tests | Optional dependency errors must remain actionable. |
| SDK-011 Wrap extraction operations | ready | unassigned | SDK-008 | SDK extraction modules and tests | Canonical import remains explicitly approved. |
| SDK-012 Wrap review operations | ready | unassigned | SDK-008 | SDK review modules and tests | Safety audit behavior remains unchanged. |
| SDK-013 Wrap export operations | ready | unassigned | SDK-008 | SDK export modules and tests | Exports are public-safe by default. |
| SDK-014 Add workflow facade | ready | unassigned | SDK-008 | `src/crime_research_kit/sdk/workflows.py`, `src/pipeline/app/service.py`, workflow tests | App layer consumes SDK facade without exposing graph nodes. |
| SDK-015 Repoint CLI handlers | ready | unassigned | SDK-009 to SDK-014 | `src/adapters/interfaces/cli/**`, CLI tests | Do not change command names or flags. |
| SDK-016 Repoint MCP tools | ready | unassigned | SDK-009 to SDK-014 | `src/adapters/interfaces/mcp/**`, MCP tests | Tool safety tiers should come from catalog where possible. |
| SDK-017 Generate or drift-check Skill API docs | ready | unassigned | SDK-005 | docs drift tests, Skill API docs | Operation docs cannot drift from the catalog. |
| SDK-018 Define private runtime policy | ready | unassigned | SDK-015, SDK-016 | packaging docs/tests | Public docs declare only `crime_research_kit.sdk`. |
| SDK-019 Update architecture docs | ready | unassigned | SDK-018 | architecture docs | System overview shows SDK as the Python public layer. |
| SDK-020 Release-note and gate pass | ready | unassigned | SDK-019 | `CHANGELOG.md`, release/gate checks | Final full-series gate. |
| SDK-021 Future HTTP route binding | ready | unassigned | SDK-005 | catalog metadata only | Backlog; no HTTP server in this series. |
| SDK-022 Move internals under `_runtime` | ready | unassigned | SDK-018 | `_runtime` migration if chosen | Backlog; only after CLI/MCP import migration. |
| SDK-023 SDK examples package | ready | unassigned | SDK-014 | SDK examples/docs | Backlog. |
| SDK-024 Catalog-driven MCP registration | ready | unassigned | SDK-016 | MCP registration code/tests | Backlog. |
| SDK-025 Strict request models | ready | unassigned | SDK-005 | request models/tests | Backlog. |

Dependency note: SDK-001 is the only unblocked implementation card at the start
of this worktree. SDK-002, SDK-003, and SDK-004 are claimed for the first
orchestration wave, but they remain dependency-gated until their preceding cards
reach review or done.

## Done

| Card | Outcome |
| --- | --- |
| SDK-000 Inventory and planning package | Deep inventory, target-shape spec, execution plan, and kanban created. |

## In Progress

| Card | Owner | Notes |
| --- | --- | --- |
| SDK-001 Freeze operation inventory | main | Critical-path local task in the SDK worktree. |

## Claimed

| Card | Owner | Notes |
| --- | --- | --- |
| SDK-002 Decide public namespace | main | Follows SDK-001 inventory; records `crime_research_kit.sdk` as the public import surface. |
| SDK-003 Add SDK package skeleton | worker-sdk-skeleton | Bounded worker slice with SDK package skeleton and import tests only. |
| SDK-004 Define public result/error types | worker-sdk-results | Bounded worker slice with result/error models and tests only. |

## Ready

| Card | Priority | Depends on | Acceptance |
| --- | --- | --- | --- |
| SDK-001 Freeze operation inventory | P0 | SDK-000 | Operation list covers CLI, MCP, ops, workflow, and Skill API docs with safety tier per operation. |
| SDK-002 Decide public namespace | P0 | SDK-001 | Namespace decision recorded; default is `crime_research_kit.sdk`; no legacy aliases. |
| SDK-003 Add SDK package skeleton | P0 | SDK-002 | `crime_research_kit.sdk` imports cleanly with README coverage and governance-friendly module sizes. |
| SDK-004 Define public result/error types | P0 | SDK-003 | `OperationResult` and `CrkError` align with Skill API response docs and support diagnostics without making subprocess output central. |
| SDK-005 Define `OperationSpec` catalog | P0 | SDK-004 | Operation specs include domain, safety tier, side effects, CLI/MCP/HTTP mappings, and request/result model names. |
| SDK-006 Add catalog parity tests | P0 | SDK-005 | Current CLI commands and MCP tools have catalog entries or explicit non-SDK exemptions. |
| SDK-007 Build `CrkContext` | P1 | SDK-004 | Context owns roots, settings, privacy defaults, and transport selection without deep modules calling settings directly. |
| SDK-008 Build `CrkClient` and `CaseClient` | P1 | SDK-007 | Case-scoped handle removes repeated `case_dir` passing for public SDK users. |
| SDK-009 Wrap case and record reads | P1 | SDK-008 | Public record reads exclude private rows by default and return `OperationResult`. |
| SDK-010 Wrap source operations | P1 | SDK-008 | Add, ingest, preserve, discover, parse, and OCR are exposed with optional dependency failures kept actionable. |
| SDK-011 Wrap extraction operations | P1 | SDK-008 | Draft/list/read/save/import operations preserve staged-write policy and explicit import approval. |
| SDK-012 Wrap review operations | P1 | SDK-008 | Validate, dedupe, identity, contradiction, privacy, public export, independence, and readiness calls return stable SDK results. |
| SDK-013 Wrap export operations | P1 | SDK-008 | Exports are public-safe by default and echo internal/private mode when requested. |
| SDK-014 Add workflow facade | P1 | SDK-008 | `client.workflows.plan/resume` expose app workflow without graph-node imports. |
| SDK-015 Repoint CLI handlers | P2 | SDK-009 to SDK-014 | Existing `cr-kit` and `crk-ledger` command tests pass with SDK-backed handlers. |
| SDK-016 Repoint MCP tools | P2 | SDK-009 to SDK-014 | Existing MCP read/write/gated tests pass with SDK-backed tools. |
| SDK-017 Generate or drift-check Skill API docs | P2 | SDK-005 | Operation docs cannot drift from catalog names, safety tiers, and envelope. |
| SDK-018 Define private runtime policy | P2 | SDK-015, SDK-016 | Public docs declare only `crime_research_kit.sdk`; implementation modules are private or moved under `_runtime`. |
| SDK-019 Update architecture docs | P2 | SDK-018 | System overview shows SDK as Python public layer and CLI/MCP as adapters. |
| SDK-020 Release-note and gate pass | P2 | SDK-019 | Changelog updated; targeted tests, `moon run crk:check`, and final `moon run crk:test` pass. |

## Backlog

| Card | Priority | Depends on | Acceptance |
| --- | --- | --- | --- |
| SDK-021 Future HTTP route binding | P3 | SDK-005 | HTTP mapping uses the catalog but no server is added in the SDK extraction series. |
| SDK-022 Move internals under `_runtime` | P3 | SDK-018 | Top-level implementation packages stop being packaged after console scripts and imports migrate. |
| SDK-023 SDK examples package | P3 | SDK-014 | Minimal examples cover case info, source ingest dry-run, packet review, public-safe export, and workflow resume. |
| SDK-024 Catalog-driven MCP registration | P3 | SDK-016 | Tool registration is generated where safe; prompts/resources remain explicit. |
| SDK-025 Strict request models | P3 | SDK-005 | Operation request models replace loose dict payloads for stable operations. |

## Blocked / Watch

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Existing worktree has unrelated docs/test changes | SDK docs or implementation could sweep in unrelated work. | Always inspect `git status --short --branch`; stage only SDK paths. |
| Historical plans still mention `src/case_builder` | Agents may implement stale paths. | New spec and plan explicitly target live top-level `src/`; archive old paths. |
| `OpResult` differs from Skill API docs | SDK could stabilize the wrong envelope. | SDK-004 and SDK-017 must align result/docs before adapters are repointed. |
| Subprocess runner leaks into SDK | Public API becomes a CLI wrapper instead of an SDK. | Transport stays private; SDK methods expose operations, not commands. |
| Optional extras become required by accident | Base install gets heavier and less local-friendly. | Packaging policy tests remain in the gate; optional methods raise dependency errors. |
