# SDK Target Shape Execution Plan

> For agentic workers: implement this plan task-by-task. Steps use checkbox
> syntax for tracking. Keep commits scoped and path-specific.

Spec: `docs/superpowers/specs/2026-07-03-sdk-target-shape.md`
Kanban: `docs/superpowers/kanban/2026-07-03-sdk-target-shape.md`

## Goal

Create a proper public Python SDK for CRK while keeping the existing CLI, MCP,
and app workflows working. The SDK should not inherit accidental legacy import
paths, historical `case_builder` assumptions, or CLI-first operation design.

## Global Constraints

- Work from `dev` or a focused `docs/*` / `feat/*` branch.
- Stage only intended paths. This repo already has unrelated docs/test changes
  in the worktree.
- Current live source layout is top-level `src/core`, `src/adapters`, and
  `src/pipeline`. Do not target historical `src/case_builder` paths.
- Every Python module stays under 200 non-comment LOC and every Python-bearing
  package keeps a `README.md`.
- Do not add required dependencies for the SDK skeleton.
- Do not add compatibility aliases for `case_builder.*`.
- Do not make top-level `adapters`, `core`, or `pipeline` a public promise.
- Existing console scripts remain stable: `cr-kit`, `crk-ledger`, `crk-mcp`.
- Safety behavior is invariant: public-safe default reads/exports, staged
  automation, explicit approval for canonical imports, no guilt/membership
  inference from proximity.

## Phase 0: Contract Freeze And Drift Inventory

**Purpose:** establish the live baseline and prevent the SDK from inheriting
historical plan drift.

**Files:**
- Read: `pyproject.toml`
- Read: `docs/guides/skill-api-spec.md`
- Read: `docs/guides/integrations/skill-api/**`
- Read: `docs/guides/architecture/system-overview.md`
- Read: `docs/guides/architecture/case-builder-langgraph.md`
- Read: `src/adapters/ops/**`
- Read: `src/adapters/interfaces/{cli,mcp}/**`
- Read: `src/pipeline/app/service.py`
- Read: `tests/runtime/**`, `tests/quality/governance/**`

**Steps:**

- [x] Record the current operation list from CLI, MCP tools, ops modules, and
  Skill API docs in one temporary inventory.
- [x] Mark each operation with domain, current function, current CLI command,
  MCP tool if present, safety tier, and current result shape.
- [x] Identify historical docs that still mention `src/case_builder`, `tcr.py`,
  or zero-required-dependency assumptions. Treat them as archives unless the
  active docs still point at them.
- [x] Decide the public import namespace. Default: `crime_research_kit.sdk`.
- [x] Commit only documentation/inventory updates if any tracked docs are
  changed.

**Acceptance:**
- There is a reviewed operation inventory.
- No implementation step depends on historical `case_builder` paths.
- The public namespace decision is explicit.

## Phase 1: SDK Skeleton And Public Types

**Purpose:** add the public namespace without moving behavior yet.

**Target files:**

```text
src/crime_research_kit/
  __init__.py
  README.md
  sdk/
    __init__.py
    README.md
    context.py
    errors.py
    results.py
    operations.py
```

Additional integration files:
- `pyproject.toml`
- `deployment/scripts/checks/fresh_build.py`
- SDK import and packaging governance tests

**Interfaces:**
- `CrkContext`
- `OperationResult`
- `CrkError` and error-code constants
- `SafetyTier`
- `OperationSpec`

**Steps:**

- [x] Add failing import tests for `crime_research_kit.sdk`.
- [x] Create the package skeleton and local READMEs.
- [x] Implement `SafetyTier` values: `read`, `staged_write`,
  `canonical_gated`, `public_export`, `internal_service`.
- [x] Implement `OperationResult` with fields aligned to Skill API docs:
  `ok`, `operation`, `case_ref`, `data`, `errors`, `warnings`, `created`,
  `updated`, `outputs`, `counts`, `diagnostics`.
- [x] Keep command/stdout/stderr diagnostic fields opt-in and not central to the
  public result contract.
- [x] Add governance tests that the new package has README coverage and remains
  within line-count limits.
- [x] Add package-discovery and built-wheel import coverage for
  `crime_research_kit.sdk`.

**Acceptance:**
- `from crime_research_kit.sdk import CrkContext, OperationResult` works.
- Built distributions include `crime_research_kit*` and the fresh-build import
  smoke imports `crime_research_kit.sdk`.
- No existing CLI/MCP behavior changes.
- No compatibility aliases are introduced.

## Phase 2: Operation Catalog

**Purpose:** make one operation catalog drive SDK, CLI/MCP parity, and docs.

**Target files:**
- `src/crime_research_kit/sdk/operations.py`
- `tests/runtime/unit/sdk/test_operations_catalog.py`
- `tests/quality/governance/docs/test_sdk_operation_docs.py`

**Steps:**

- [x] Define `OperationSpec` with name, domain, safety tier, request model name,
  result model name, side effects, CLI mapping, MCP mapping, and future HTTP
  mapping.
- [x] Add specs for the initial stable set: case info/create, records list,
  source text, add/ingest/preserve/discover/parse/ocr, draft/list/read/save
  extraction, import reviewed extraction, link names, public-record planning,
  validation, review audits, public-safe exports, workflow plan/resume.
- [ ] Add parity tests proving every current MCP tool and relevant CLI command
  has a catalog entry or an explicit "not SDK" exemption.
- [ ] Add docs generation or a drift check that compares Skill API operation
  docs to the catalog.
- [x] Keep operation names snake_case internally and define camelCase/docs names
  as metadata, not separate behavior.

**Acceptance:**
- Operation metadata is no longer implicit in interface wrappers.
- CLI/MCP/doc drift is testable.

## Phase 3: Case-Scoped SDK Client

**Purpose:** expose useful Python methods over the current ops without leaking
the current ops module layout.

Dependency gate: do not begin case-scoped wrappers until the SDK operation
catalog has landed. Wrapper methods should consume catalog names and safety
metadata instead of copying interface-local metadata.

**Target files:**

```text
src/crime_research_kit/sdk/
  client.py
  cases.py
  sources.py
  extractions.py
  review.py
  exports.py
```

**Steps:**

- [ ] Add tests using `data/examples/synthetic_case` and temp copies.
- [ ] Implement `CrkClient(context)` and `client.case(slug_or_path)`.
- [ ] Implement `CaseClient` with case-rooted methods; callers should not pass
  `case_dir` repeatedly after obtaining a case handle.
- [ ] Wrap existing ops behind SDK methods, converting `OpResult` into
  `OperationResult`.
- [ ] Make `include_private` explicit on reads/exports, defaulting to false.
- [ ] Make canonical import method name explicit, for example
  `case.extractions.import_reviewed(packet, approved=True)`.
- [ ] Add dependency-error tests for optional retrieval/OCR/discovery methods
  when extras are absent.

**Acceptance:**
- A Python user can create a client, inspect a case, read public records, stage
  extraction packets, and plan review/export operations through SDK methods.
- Safety defaults match current ops and MCP tests.

## Phase 4: Workflow SDK Facade

**Purpose:** expose app-layer workflow without making graph internals public.

Dependency gate: do not begin workflow facade work until the SDK operation
catalog has landed. The app service should consume a `WorkflowClient` or
catalog-backed services, with subprocess transport kept private.

**Target files:**
- `src/crime_research_kit/sdk/workflows.py`
- `src/pipeline/app/service.py`
- `tests/runtime/e2e/test_sdk_workflows.py`

**Steps:**

- [ ] Define workflow request/result models for plan and resume.
- [ ] Implement `client.workflows.plan(...)` and `client.workflows.resume(...)`
  over the existing app service.
- [ ] Repoint `pipeline/app/service.py` to use SDK/context objects where it
  simplifies the boundary, but keep graph nodes private.
- [ ] Preserve sequential dry-run behavior and LangGraph checkpoint behavior.
- [ ] Prove packet review and export review gates still fail closed without
  approvals.

**Acceptance:**
- SDK workflow methods can dry-run, pause, resume, and report status through
  SDK/catalog-backed services without importing graph nodes.
- `pipeline/app/service.py` no longer owns duplicated operation metadata or
  public safety-tier definitions.
- Existing `cr-kit plan` and `cr-kit resume` tests still pass.

## Phase 5: Repoint CLI And MCP To SDK/Catalog

**Purpose:** make CLI and MCP true adapters over the SDK instead of parallel
operation surfaces.

Dependency gate: do not repoint CLI or MCP until the operation catalog and
catalog parity tests have landed.

**Files:**
- `src/adapters/interfaces/cli/**`
- `src/adapters/interfaces/mcp/**`
- `tests/runtime/integration/test_mcp_tools_read.py`
- `tests/runtime/integration/test_mcp_tools_write_gated.py`
- `tests/quality/governance/docs/test_runbook_coverage.py`

**Steps:**

- [ ] Repoint CLI handlers to SDK clients while preserving command names and
  flags.
- [ ] Repoint MCP tool functions to SDK clients or catalog-dispatched
  operations.
- [ ] Keep MCP resources/prompts as MCP-specific content, but remove duplicated
  operation tier metadata where catalog can drive it.
- [ ] Update tests to assert SDK/catalog parity rather than hand-maintained
  duplicate lists.
- [ ] Preserve current error text where runbooks rely on it, but ensure the
  underlying error code comes from SDK errors/results.

**Acceptance:**
- Existing CLI and MCP tests pass.
- Operation safety tiers are defined once.

## Phase 6: Packaging Boundary And Private Runtime

**Purpose:** stop publishing implementation layout as the SDK.

**Files:**
- `pyproject.toml`
- `src/crime_research_kit/_runtime/**` if moving files
- import-boundary tests

**Steps:**

- [ ] Decide whether to move implementation modules under
  `crime_research_kit._runtime` now or mark top-level packages as temporary
  internal implementation in packaging docs.
- [ ] If moving, move in small domain slices with import-boundary tests.
- [ ] If not moving yet, add explicit docs saying only `crime_research_kit.sdk`
  is public pre-1.0 Python API.
- [ ] Update package discovery only when console scripts and internal imports
  have been migrated.
- [ ] Add a governance test that public docs do not advertise top-level
  implementation imports.

**Acceptance:**
- SDK consumers have one public namespace.
- Internal implementation can still evolve without compatibility promises.

## Phase 7: Documentation, Release Notes, And Gate

**Files:**
- `README.md`
- `docs/guides/integrations/skill-api/**`
- `docs/guides/architecture/system-overview.md`
- `docs/guides/architecture/case-builder-langgraph.md`
- `CHANGELOG.md`

**Steps:**

- [ ] Add a developer-integrator SDK quick start after the SDK works.
- [ ] Generate or update operation reference docs from the catalog.
- [ ] Update architecture docs to show SDK as the public Python layer and
  CLI/MCP as adapters.
- [ ] Update changelog under `Unreleased`.
- [ ] Run `moon run crk:check`.
- [ ] Run targeted SDK, MCP, CLI, workflow, and governance tests.
- [ ] Run `moon run crk:test` before merging the full series.

**Acceptance:**
- Docs describe the new public SDK shape without preserving historical imports.
- The local gate is green.

## Cut Lines

Keep these as separate reviewable commits or branches:

1. SDK skeleton and public types.
2. Operation catalog and drift tests.
3. Case-scoped SDK client.
4. Workflow facade.
5. CLI/MCP repoint.
6. Packaging/private-runtime boundary.
7. Docs and release notes.

Do not mix report-renderer refactors, vocabulary-pack work, course-doc moves,
or unrelated governance cleanup into this SDK series.
