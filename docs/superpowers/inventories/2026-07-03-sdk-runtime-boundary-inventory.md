# SDK-022 Runtime Boundary Inventory

Date: 2026-07-03
Status: runtime migration in verification
Task: SDK-022 Move internals under `_runtime`

SDK-022 moves the private runtime modules from top-level implementation
packages into `crime_research_kit._runtime` without adding legacy compatibility
aliases. Public Python callers remain on `crime_research_kit.sdk`; console
script names remain `cr-kit`, `crk-ledger`, and `crk-mcp`.

Top-level `adapters.*`, `core.*`, and `pipeline.*` are not public SDK imports
and are no longer package-discovery targets. Internal callers should use
`crime_research_kit._runtime.*`; public integrations should use
`crime_research_kit.sdk`.

## Runtime Shape

```text
src/crime_research_kit/
  _runtime/
    adapters/
    core/
    pipeline/
    cli.py
```

## Packaging State

Live `pyproject.toml` state on this branch:

| Surface | Current state | Runtime-boundary implication |
| --- | --- | --- |
| Distribution | `name = "crime-research-kit"`, `version = "0.13.15"` | Distribution name stays unchanged; version bumps with the release commit. |
| Console scripts | `cr-kit = "crime_research_kit._runtime.cli:main"`; `crk-ledger = "crime_research_kit._runtime.adapters.interfaces.cli.entry:main"`; `crk-mcp = "crime_research_kit._runtime.adapters.interfaces.mcp.server:main"` | Command names stay stable while private implementation paths move under the package namespace. |
| Package discovery | `where = ["src"]`; `include = ["crime_research_kit*"]`; `namespaces = true` | Top-level `adapters*`, `core*`, and `pipeline*` are no longer packaged. |
| Lane package data | key `"crime_research_kit._runtime.core.lanes"` | Lane registry data ships with the moved runtime package. |
| Schema package data | key `"crime_research_kit._runtime.core.models"` | Record schemas ship with the moved runtime package. |
| Report template data | key `"crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages"` | Report page assets move with the renderer package. |

## Move Map

| Before SDK-022 | After SDK-022 |
| --- | --- |
| `src/adapters/**` | `src/crime_research_kit/_runtime/adapters/**` |
| `src/core/**` | `src/crime_research_kit/_runtime/core/**` |
| `src/pipeline/**` | `src/crime_research_kit/_runtime/pipeline/**` |
| `src/cli.py` | `src/crime_research_kit/_runtime/cli.py` |

The move is intentionally mechanical at this stage. It preserves existing CLI,
MCP, SDK facade, workflow, report, lane, and schema behavior while narrowing the
installed runtime namespace.

## Cleared Blockers

| Blocker | Resolution |
| --- | --- |
| Console scripts pointed at top-level modules. | Script targets now point at `crime_research_kit._runtime.*` modules. |
| `CrkRunner` launched `python -m adapters.interfaces.cli`. | Runner launches `python -m crime_research_kit._runtime.adapters.interfaces.cli`. |
| Package data was keyed to `core.*` and `adapters.*`. | Package-data keys now use `crime_research_kit._runtime.*`. |
| Lane and schema loaders used top-level resource names. | `importlib.resources.files(...)` calls use the `_runtime` package names. |
| SDK lazy imports pointed at top-level runtime modules. | SDK facades lazy-import `_runtime` modules while preserving optional dependency boundaries. |
| MCP dynamic tool imports used `adapters.interfaces.mcp.tools.*`. | Dynamic imports now use `crime_research_kit._runtime.adapters.interfaces.mcp.tools.*`. |
| Governance allowed top-level package discovery. | Packaging policy now expects only `crime_research_kit*` in package discovery. |

## Verification Matrix

Minimum checks for completing SDK-022:

- `python -m compileall src`
- `python -c "import crime_research_kit.sdk"`
- `python -c "from crime_research_kit.sdk import CrkClient, CrkContext"`
- `python -m crime_research_kit._runtime.adapters.interfaces.cli --help`
- `cr-kit --help`
- `crk-ledger --help`
- MCP server import smoke for `crime_research_kit._runtime.adapters.interfaces.mcp.server`.
- Lane registry tests and docs generation tests.
- Schema loading and record model tests.
- Report renderer tests plus package-data smoke.
- SDK wrapper tests for case, source, extraction, review, export, retrieval,
  names, examples, and workflow methods.
- Workflow dry-run, resume, and review-gate tests.
- Packaging policy tests, public SDK boundary tests, and optional-import tests.

## Guardrails

- Do not add `case_builder.*` aliases.
- Do not add top-level `adapters`, `core`, or `pipeline` compatibility shims.
- Do not document `_runtime` as public SDK API.
- Keep `import crime_research_kit.sdk` light; optional OCR, MCP, LangGraph,
  retrieval, memory, and LLM dependencies must stay lazy.
- Treat `run_report` as a direct MCP/runtime exception until evidence-board
  public/private filtering semantics are explicit.
