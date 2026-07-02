# src + Skills Stabilization Design

**Date:** 2026-07-02
**Status:** Approved design, pending implementation plans
**Scope:** `src/`, `pyproject.toml`, `docs/registry/`, `docs/schemas/` packaging, governance tests, report frontend

## Problem

The `refactor/decompose-tcr-cli` merge (02d27aa) moved ~7,800 lines from the single-file
`tcr.py` skill script into 112 modules under `src/`. The decomposition preserved behavior,
which means it also preserved two classes of debt:

1. **Static, non-generalized code.** The analysis classifiers embed keyword vocabulary from
   one specific research case — terms such as `promis`, `inslaw`, `finders`, `jonestown`,
   `narconon`, `monarch`, `montauk`, `based on hubbard` — inside general-purpose code
   (`src/adapters/ops/evidence/reports/analysis/relationships.py`, `paths.py`). Constant
   tables in `layered/vocab.py` and `classifiers.py` duplicate vocabulary the repo declares
   canonical in `docs/registry/`. `records/validation.py::load_schema()` guesses schema
   locations by walking CWD/parents with hardcoded relative paths (including the repo's own
   folder name `tc-c-kit/docs/schemas`), which breaks when the package is installed outside
   the repo.
2. **Hand-rolled infrastructure.** Required-field validation instead of the JSON Schema
   files that already exist in `docs/schemas/`; `urllib.request` fetching without retries;
   hand-rolled env parsing in `core/config.py`; two argparse CLIs; and ~1,100 lines of
   string-built HTML/SVG report rendering.

## Decisions (made with the operator)

- **Dependency policy is relaxed.** The package moves from zero required dependencies to a
  small required set: `jsonschema`, `pydantic` (v2), `pydantic-settings`, `httpx`, `typer`,
  `jinja2`.
- **Pydantic usage contract.** `BaseModel` is the typed in-memory representation for CRK
  evidence records, extraction packets, manifests, schema-backed payloads, and serialized
  artifacts. `BaseSettings` appears only at process boundaries — CLI startup, MCP server
  startup, deployment/runtime config — instantiated once, with values passed inward; core
  logic never calls `Settings()` itself.
- **Vocabulary lives in the registry with per-case overrides.** Neutral default packs ship
  as `docs/registry/` shards; case-specific terms leave the codebase and become per-case
  override packs.
- **Reports become data model + templates.** Builders emit a typed JSON data model;
  presentation is prebuilt htmx + Tailwind templates rendered via Jinja2.
- **Asset shipping:** TS/Tailwind compile at dev time via a moon task; static assets are
  committed; operators need no Node and exports stay offline-viewable. (Chosen by default
  when the question timed out; overridable before stage 4 planning.)

## Non-goals

- No changes to the ledger record schemas or the safety contract semantics.
- No rewrite of optional-extra subsystems (parsing, retrieval, memory, acquisition-search)
  beyond the HTTP client swap.
- Skills under `.agents/skills/` need no migration work: zero stale `tcr.py` references
  remain (111 `crk-ledger` references confirmed). Historical specs/plans that mention
  `tcr.py` are archives and stay as-is.

## Architecture: four sequenced sub-projects

Each stage is an independently mergeable spec → plan → branch cycle off `dev`. Later stages
consume earlier ones (pydantic models feed the report data model; registry packs feed the
classifiers). Each stage keeps modules under 200 non-comment LOC, respects directory shape
governance, and passes `moon run crk:test-governance` before merge.

### Stage 1 — Dependency policy + core stabilization

- `pyproject.toml`: add required dependencies `jsonschema`, `pydantic>=2`,
  `pydantic-settings`, `httpx`, `typer`, `jinja2`. Deduplicate extras that currently pull
  these transitively.
- Update `tests/quality/governance/platform/test_packaging_policy.py` (line 62,
  `test_core_package_has_no_runtime_dependencies_and_declares_license` asserts
  `dependencies == []`) to assert the new allowlist instead — the test still pins the set so
  dependencies cannot grow silently.
- Update CLAUDE.md and AGENTS.md "no required dependencies" language to describe the new
  contract: small pinned required set, heavier features still behind extras with graceful
  degradation.
- Package `docs/schemas/` as package data; replace `load_schema()` path-guessing with
  `importlib.resources` lookup (repo-checkout fallback retained for dev workflows).
- Replace the hand-rolled required-field checker in
  `src/adapters/ops/casework/records/validation.py` with `jsonschema` validation against
  the real schema files. Error output stays line-addressed (`records/<file>.jsonl:<n>`) so
  existing operator workflows and tests keep working.
- Convert `core/config.py` to a `pydantic-settings` `BaseSettings` class (same `CRK_*` env
  vars, same defaults). Settings objects are constructed once at process boundaries — CLI
  startup (`cr-kit`, `crk-ledger`), MCP server startup, deployment/runtime config — and
  their values are passed inward as plain arguments or models; nothing under `core/`,
  `pipeline/`, or `adapters/ops/` calls `Settings()` directly. Introduce `BaseModel` classes for the typed in-memory surface: CRK evidence
  records (sources, claims, entities, events, relationships, …), extraction packets,
  manifests, `OpResult`, and other serialized artifacts. The JSON Schema files in
  `docs/schemas/` remain the canonical on-disk ledger contract; the pydantic models mirror
  them and a governance drift test keeps model fields aligned with schema fields. Internal
  dict plumbing converts to models opportunistically, not exhaustively.

### Stage 2 — Vocabulary externalization

- New `docs/registry/` shards define neutral default classification packs:
  - relationship-facet term packs (replacing the inline lists in
    `analysis/relationships.py` and `paths.py`),
  - layer ordering (`layered/vocab.py::LAYER_ORDER_MAP`),
  - status/grade score tables (`classifiers.py::STATUS_SCORE`, `GRADE_SCORE`).
- Case-specific terms move to an example per-case override pack under
  `data/examples/synthetic_case/`, with the pack format documented. At runtime a case may
  override/extend defaults via a vocabulary file in `data/cases/<slug>/`.
- Classifiers become generic pack-driven matchers. Records matching no pack fall through to
  an explicit `unclassified` bucket — the current silent `personnel_bridge` default
  disappears. This strengthens the safety contract: no thematic label is implied that the
  packs (and therefore the operator) did not define.
- Governance drift tests extend to the new shards, same pattern as the existing
  lane-registry drift checks.

### Stage 3 — CLI and acquisition swaps

- `adapters/io/acquisition/http.py`: `urllib.request` → `httpx` with explicit timeouts,
  redirect handling, and retry-on-transient (connect errors, 5xx). Same
  `fetch_url() -> (content_type, body, headers)` contract.
- Both CLIs (`cr-kit` in `src/cli.py` + `adapters/interfaces/cli/` for `crk-ledger`)
  migrate from argparse to typer. Every existing command name, argument, and flag signature
  is preserved verbatim so skills, docs, and muscle memory need no changes. Typer over
  click because the codebase is standardizing on type-hint-driven interfaces (pydantic).

### Stage 4 — Report template layer

- Report builders under `adapters/ops/evidence/reports/` stop emitting HTML/SVG strings and
  produce a typed JSON data model (pydantic models from stage 1): pages, facets, network
  layers, matrices, charts.
- Presentation moves to prebuilt htmx + Tailwind templates:
  - a `frontend/` source tree (TS + Tailwind) compiled by a dev-time moon task,
  - compiled static assets committed to the repo,
  - Python renders the data model into templates with Jinja2 at export time.
  - No Node required on operator machines; exports remain self-contained and offline-viewable.
- SVG network/matrix renderers become templates fed by the same data model.
- Parity gate: old and new renderers run side-by-side against
  `data/examples/synthetic_case/` until output parity (content, not byte-identity) is
  confirmed; then the string-builder renderers are deleted.

## Error handling

- `jsonschema` validation failures report record file, line number, and JSON pointer path;
  exit codes match current validate behavior.
- `httpx` fetch failures surface the same error shape ingest handles today; retries are
  bounded (3 attempts, backoff) and logged in the source record notes as before.
- Missing per-case vocabulary pack is not an error: defaults apply. A malformed pack fails
  fast with a line-addressed parse error.
- Template rendering failures fail the export command; partially written export files are
  not left behind (write to temp, move on success).

## Testing

- Each stage lands with its own tests in the matching lane (`unit` for pack matching and
  models, `integration` for validate/ingest/export flows, `governance` for the new registry
  drift checks and the updated packaging policy).
- Stage 4's parity gate is an integration test comparing data-model-driven output against
  the synthetic case fixture.
- `moon run crk:check` and `moon run crk:test` green at every merge.

## Sequencing and branches

| Stage | Branch | Depends on |
|-------|--------|------------|
| 1. Deps + core stabilization | `refactor/required-deps-core` | — |
| 2. Vocabulary externalization | `refactor/vocab-registry-packs` | 1 |
| 3. CLI + acquisition swaps | `refactor/typer-httpx` | 1 |
| 4. Report template layer | `feat/report-template-layer` | 1 (models), 2 (packs) |

Stages 2 and 3 are independent of each other and can proceed in parallel. Each stage gets
its own implementation plan via the writing-plans skill before any code is written.
