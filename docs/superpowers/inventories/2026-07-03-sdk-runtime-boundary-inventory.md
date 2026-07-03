# SDK-022 Runtime Boundary Inventory

Date: 2026-07-03
Status: inventory-only guardrail
Task: SDK-022 Move internals under `_runtime`

This slice does not move runtime modules. It records the live blockers and move
order for a later migration from top-level `src/adapters`, `src/core`, and
`src/pipeline` into `src/crime_research_kit/_runtime`.

The public Python SDK remains `crime_research_kit.sdk`. Top-level
`adapters.*`, `core.*`, and `pipeline.*` are private runtime packages, not
compatibility promises. The later move should not add `case_builder.*` aliases
or top-level compatibility shims.

## Target Runtime Shape

Later migration target:

```text
src/crime_research_kit/
  _runtime/
    adapters/
    core/
    pipeline/
```

The move should keep public callers on `crime_research_kit.sdk` and keep command
names stable: `cr-kit`, `crk-ledger`, and `crk-mcp`.

## Current Packaging State

Live `pyproject.toml` state observed on this branch:

| Surface | Current state | Runtime-boundary implication |
| --- | --- | --- |
| Distribution | `name = "crime-research-kit"`, `version = "0.13.14"` | Distribution name stays unchanged. |
| Top-level module | `[tool.setuptools] py-modules = ["cli"]` | `cr-kit` currently enters through the top-level `cli` module. Decide later whether to keep this as a tiny shim or repoint the script. |
| Console scripts | `cr-kit = "cli:main"`; `crk-ledger = "adapters.interfaces.cli.entry:main"`; `crk-mcp = "adapters.interfaces.mcp.server:main"` | Do not remove top-level package discovery until script targets no longer require top-level `adapters`. |
| Package discovery | `where = ["src"]`; `include = ["adapters*", "core*", "pipeline*", "crime_research_kit*"]`; `namespaces = true` | The three top-level runtime package globs are temporary but required today. |
| Lane package data | key `"core.lanes"` with `registry_data/*.json`, `registry_data/lanes/*.json`, `registry_data/templates/*.json`, and `registry_data/analysis/*.json` | Must become a `_runtime.core.lanes` package-data key and matching `importlib.resources` lookup. |
| Schema package data | key `"core.models"` with `schemas_data/{case,evidence,review}/*.json` | Must become a `_runtime.core.models` package-data key and matching schema lookup. |
| Report template data | key `"adapters.ops.evidence.reports.analysis.pages"` with `templates_data/static/*`, `templates_data/layouts/*.j2`, and `templates_data/figures/*.j2` | Must move with report package metadata. Renderer uses `Path(__file__)`, so the file move is viable only if wheel package data follows it. |

## Rough Evidence Counts

These are rough migration-size numbers from `find` and `rg`, not an exhaustive
file manifest.

| Runtime root | Files | Python files | Notable contents |
| --- | ---: | ---: | --- |
| `src/adapters` | 171 | 127 | Ops, CLI/MCP/LLM interfaces, optional IO, report renderers/templates. |
| `src/core` | 49 | 19 | Casefile/config helpers, models, lane registry, packaged schema/registry data. |
| `src/pipeline` | 19 | 12 | Workflow app service, graph runner, graph nodes, review gates, checkpointing. |
| Total | 239 | 158 | Broad enough that a later move should be guarded by import and packaging tests. |

Import evidence from `rg --glob '*.py'` across `src` and `tests`:

| Pattern family | Import lines |
| --- | ---: |
| Any top-level `adapters`, `core`, or `pipeline` import | 499 lines in 154 files |
| `adapters` imports | 351 |
| `core` imports | 107 |
| `pipeline` imports | 41 |
| Runtime-code-only `adapters` imports under `src` | 263 |
| Runtime-code-only `core` imports under `src` | 78 |
| Runtime-code-only `pipeline` imports under `src` | 17 |

Resource evidence:

| Resource area | Count evidence | Current loader |
| --- | ---: | --- |
| `src/core/lanes/registry_data` | 10 files | `files("core.lanes").joinpath("registry_data")` in `core.lanes.registry`. |
| `src/core/models/schemas_data` | 13 files including local README | `files("core.models").joinpath("schemas_data")` in record validation. |
| `src/adapters/ops/evidence/reports/analysis/pages/templates_data` | 6 files in the directory; 5 runtime assets matched by package-data patterns | `Path(__file__).resolve().parent / "templates_data"` in the page renderer. |

## High-Risk Blockers

### 1. Console scripts and subprocess CLI module

Current blockers:

- `crk-ledger` points at `adapters.interfaces.cli.entry:main`.
- `crk-mcp` points at `adapters.interfaces.mcp.server:main`.
- `cr-kit` points at `cli:main`, and `src/cli.py` imports
  `adapters.interfaces.cli.case_builder`.
- `CrkRunner` builds subprocess commands with
  `python -m adapters.interfaces.cli`.
- `tests/helpers.py` mirrors `LEDGER_CLI_MODULE = "adapters.interfaces.cli"`.

Migration rule:

- Keep command names stable, but update script targets and runner module names
  before dropping `adapters*` from package discovery.
- If `src/cli.py` stays, keep it as a tiny console-script shim only. Do not
  document `import cli` as a public API.
- Dry-run diagnostics and tests that assert command lists will need the new
  module path, likely `crime_research_kit._runtime.adapters.interfaces.cli`.

### 2. Package-data resource names

Current blockers:

- Lane registry fallback uses `files("core.lanes")`.
- Schema fallback uses `files("core.models")`.
- `pyproject.toml` package-data keys are keyed to `core.lanes`, `core.models`,
  and `adapters.ops.evidence.reports.analysis.pages`.
- Packaging policy tests compare canonical docs to the current package-data
  directories under `src/core/...`.
- Report frontend asset tests pin the current
  `src/adapters/ops/evidence/reports/analysis/pages/templates_data/static`
  path.

Migration rule:

- Move resource packages and package-data keys in the same commit as their
  loaders.
- Update tests to compare canonical docs against the `_runtime` package-data
  directories.
- Run a built-wheel smoke that imports the moved runtime package and renders a
  report page from installed package data.

### 3. SDK lazy imports

The public SDK modules currently keep runtime imports mostly inside methods, but
they still point at top-level runtime packages.

Observed SDK files with lazy runtime imports:

- `src/crime_research_kit/sdk/cases.py`
- `src/crime_research_kit/sdk/sources.py`
- `src/crime_research_kit/sdk/extractions.py`
- `src/crime_research_kit/sdk/review.py`
- `src/crime_research_kit/sdk/exports.py`
- `src/crime_research_kit/sdk/names.py`
- `src/crime_research_kit/sdk/retrieval.py`
- `src/crime_research_kit/sdk/workflows.py`

Migration rule:

- Rewrite these imports to `_runtime` paths while preserving lazy optional
  imports.
- Keep `import crime_research_kit.sdk` light. It must not start importing OCR,
  MCP, LangGraph, retrieval, memory, or other optional dependencies eagerly.
- Add or retain a guard that rejects SDK lazy imports from top-level
  `adapters`, `core`, or `pipeline` after the move.

### 4. MCP dynamic imports and direct exceptions

Current blockers:

- MCP console script points at `adapters.interfaces.mcp.server:main`.
- MCP tool registration dynamically imports
  `adapters.interfaces.mcp.tools.{module}`.
- MCP tests import `adapters.interfaces.mcp.*` directly.
- `run_report` remains a direct MCP/runtime exception because the
  evidence-board report still lacks explicit public/private filtering semantics.

Migration rule:

- Update the dynamic import base to the `_runtime` namespace in the same commit
  as the MCP package move.
- Keep prompts/resources explicit MCP content.
- Keep `run_report` direct until its privacy semantics are resolved; do not
  promote it as a public SDK operation just to simplify the move.

### 5. Workflow service and graph imports

Current blockers:

- `src/pipeline/app/service.py` imports `adapters.ops.runner`,
  `core.models.state`, and `pipeline.graph.*`.
- SDK workflow methods lazy-import `core.models.state` and
  `pipeline.app.service`.
- Graph runner and graph nodes import `adapters.ops`, `core.models.state`, and
  other `pipeline.graph` modules.

Migration rule:

- Move `pipeline` after `core` and `adapters` import paths are ready, because
  it depends on both.
- Update SDK workflow lazy imports and app service imports together.
- Preserve sequential dry-run, LangGraph checkpoint, packet-review gate, and
  export-review gate behavior.

## Risk-Ranked Move Order

| Order | Move or guardrail | Risk | Why this order |
| ---: | --- | --- | --- |
| 0 | Keep this inventory as the SDK-022 guardrail. | Low | Establishes that no runtime modules moved in this slice. |
| 1 | Lock packaging/import guardrails before file moves. | High | Prevents dropping `adapters*`, `core*`, or `pipeline*` while scripts or package-data keys still point at top-level packages. |
| 2 | Move `core` to `_runtime.core` and update all `core.*` imports, package-data keys, and `files("core.*")` lookups. | High | `core` is the shared foundation. A partial move breaks lanes, schemas, record models, workflow state, and many tests. |
| 3 | Move `adapters` to `_runtime.adapters` and update SDK lazy imports, CLI/MCP imports, runner module names, and report package-data metadata. | Highest | This touches console scripts, subprocess execution, MCP registration, optional IO, and report templates. |
| 4 | Move `pipeline` to `_runtime.pipeline` and update workflow service, graph self-imports, SDK workflow lazy imports, and graph tests. | Medium-high | Pipeline depends on the moved `core` and `adapters` packages and should move after those paths settle. |
| 5 | Remove `adapters*`, `core*`, and `pipeline*` from package discovery. | High | Only safe after scripts, package data, runtime imports, tests, and docs no longer require top-level packages. |

If the implementation cannot stay green after each root move without temporary
aliases, prefer one tightly scoped mechanical move commit with strong preflight
and postflight tests over adding compatibility shims. The project policy is to
fix callers, not preserve top-level runtime imports.

## Later Verification Matrix

Minimum checks for the later code-moving task:

- `python -c "import crime_research_kit.sdk"`
- `python -c "from crime_research_kit.sdk import CrkClient, CrkContext"`
- `python -m crime_research_kit._runtime.adapters.interfaces.cli --help`
- `cr-kit --help`
- `crk-ledger --help`
- MCP server import smoke for the new script target.
- Lane registry tests and docs generation tests.
- Schema loading and record model tests.
- Report renderer tests plus built-wheel report-template package-data smoke.
- SDK wrapper tests for case, source, extraction, review, export, retrieval,
  names, and workflow methods.
- Workflow dry-run, resume, and review-gate tests.
- Packaging policy tests, public SDK boundary tests, and optional-import tests.

Do not treat this inventory check as proof that the runtime move is complete.
It only scopes the later migration and names the blockers that must be cleared
before top-level runtime package discovery can be removed.
