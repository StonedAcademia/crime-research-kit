# Python SDK Boundary And Quick Start

Status: pre-1.0 public API policy.

The public Python SDK import root is `crime_research_kit.sdk`.

```python
from crime_research_kit.sdk import CrkClient, CrkContext
```

The distribution packages private implementation modules under
`crime_research_kit._runtime` because the console scripts and app runtime need
them. That namespace is internal, not a supported SDK import, and may be
reshaped before 1.0 without compatibility aliases.

Do not build integrations against `adapters.*`, `core.*`, `pipeline.*`, or
historical `case_builder.*` paths. If an operation is missing from the SDK,
promote it under `crime_research_kit.sdk` with tests and catalog metadata
instead of documenting a runtime module as public API.

## Quick Start

Read operations use public-safe defaults. `include_private` defaults to `False`
unless a caller opts in through `CrkContext` or an explicit method argument.

```python
from pathlib import Path

from crime_research_kit.sdk import CrkClient, CrkContext

client = CrkClient(CrkContext(cases_root=Path("data/examples")))
case = client.case("synthetic_case")

info = case.info()
sources = case.records.list("sources", limit=10)

assert info.ok
assert sources.ok
```

SDK methods return `OperationResult` objects. Use `result.ok`, `result.data`,
`result.errors`, `result.warnings`, `result.outputs`, and `result.diagnostics`
instead of parsing CLI stdout.

Staged writes and optional services stay explicit:

```python
client = CrkClient(CrkContext(cases_root=Path("data/cases"), dry_run=True))
case = client.case("example_case")

result = case.sources.add(
    title="Archive index lead",
    url="https://example.org/archive",
    source_type="archive",
    public_export=False,
)
```

Canonical imports stay gated. A reviewed packet import requires an explicit
approval flag at the SDK boundary:

```python
result = case.extractions.import_reviewed("SDEMO0001_extraction.json", approved=True)
```

For operation names, safety tiers, CLI/MCP mappings, and future HTTP metadata,
use the SDK catalog:

```python
for operation in client.operations("sources"):
    print(operation.name, operation.safety_tier.value)
```

## Importable Recipes

`crime_research_kit.sdk.examples` contains small importable recipes for common
integration flows. They are examples built on `CrkClient`, `CrkContext`, and
SDK operation methods, not a new runtime layer or a separate compatibility
surface.

```python
from pathlib import Path

from crime_research_kit.sdk.examples import source_ingest_dry_run_example

result = source_ingest_dry_run_example(
    "https://example.org/source",
    cases_root=Path("data/cases"),
    case_slug="example_case",
)
```

The examples package covers these recipes:

| Recipe | Use it for |
| --- | --- |
| `case_info_example` | Read public-safe case metadata and record counts. |
| `source_ingest_dry_run_example` | Preview URL source ingestion without committing writes. |
| `packet_review_example` | Check staged extraction packets before gated import. |
| `public_safe_export_example` | Run public-safe export checks and export helpers with private records excluded by default. |
| `workflow_resume_example` | Resume a paused workflow with packet review and export decisions. |

## Current Boundary

| Surface | Stability | Notes |
| --- | --- | --- |
| `crime_research_kit.sdk` | Public pre-1.0 SDK | Stable entrypoint for Python callers. |
| `cr-kit`, `crk-ledger`, `crk-mcp` | Public command surfaces | Console scripts remain supported separately from Python imports. |
| `crime_research_kit._runtime.*` | private runtime | Packaged for current implementation and scripts only. |
| `adapters.*`, `core.*`, `pipeline.*` | Removed private layout | Not packaged as public SDK imports. |
| `case_builder.*` | Historical | No compatibility aliases will be added. |

## Runtime Migration Rule

The private runtime namespace is `crime_research_kit._runtime`. Console scripts,
package-data resources, SDK lazy imports, MCP wiring, and workflow imports must
stay on that private namespace rather than top-level runtime packages.

Do not add compatibility aliases for the historical top-level modules. During
the migration, fix callers to use `crime_research_kit.sdk` for public
operations or `crime_research_kit._runtime` for internal implementation code.

## Promotion Rule

New Python integration points start as runtime implementation and become public
only when they are exposed from `crime_research_kit.sdk`, covered by tests, and
represented in the SDK operation catalog where they are operations.

## Reference Docs

The Skill API operation reference is checked against
`crime_research_kit.sdk.operations.list_operations()` by
`tests/quality/governance/docs/test_sdk_operation_docs.py`. Update the catalog
first, then refresh `docs/guides/integrations/skill-api/operations/README.md`
and the operation detail pages.
