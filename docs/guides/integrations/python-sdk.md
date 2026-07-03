# Python SDK Boundary

Status: pre-1.0 public API policy.

The public Python SDK import root is `crime_research_kit.sdk`.

```python
from crime_research_kit.sdk import CrkClient, CrkContext
```

The distribution still packages implementation modules such as `adapters`,
`core`, and `pipeline` because the current console scripts and app runtime need
them. Those top-level modules are runtime internals, not supported SDK imports,
and they may move or be renamed before 1.0 without compatibility aliases.

Do not build integrations against `adapters.*`, `core.*`, `pipeline.*`, or
historical `case_builder.*` paths. If an operation is missing from the SDK,
promote it under `crime_research_kit.sdk` with tests and catalog metadata
instead of documenting a runtime module as public API.

## Current Boundary

| Surface | Stability | Notes |
| --- | --- | --- |
| `crime_research_kit.sdk` | Public pre-1.0 SDK | Stable entrypoint for Python callers. |
| `cr-kit`, `crk-ledger`, `crk-mcp` | Public command surfaces | Console scripts remain supported separately from Python imports. |
| `adapters.*`, `core.*`, `pipeline.*` | private runtime | Packaged for current implementation and scripts only. |
| `case_builder.*` | Historical | No compatibility aliases will be added. |

## Promotion Rule

New Python integration points start as runtime implementation and become public
only when they are exposed from `crime_research_kit.sdk`, covered by tests, and
represented in the SDK operation catalog where they are operations.
