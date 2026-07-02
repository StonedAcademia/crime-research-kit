# Test Layout

Tests are grouped by the kind of confidence they provide.

| Directory | Purpose | Typical command |
| --- | --- | --- |
| `runtime/unit/` | Pure functions, small policy helpers, parser/model behavior without full workflow orchestration. | `moon run crk:test-unit` |
| `runtime/integration/` | Ops, CLI-adjacent, filesystem, source ledger, export, and component-boundary tests. | `moon run crk:test-integration` |
| `runtime/e2e/` | End-to-end orchestration through graph, service, or MCP session boundaries. Optional extras may skip tests. | `moon run crk:test-e2e` |
| `quality/governance/` | Repository policy, schemas, generated docs, lane registry, and skill-doc drift checks. | `moon run crk:test-governance` |
| `quality/smoke/` | Fast heartbeat checks for the main case-builder path. | `moon run crk:test-smoke` |

`tests/conftest.py` automatically marks tests with the marker matching the
nearest known category in the path, so `-m unit`, `-m integration`, `-m e2e`,
`-m governance`, and `-m smoke` also work through
`uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest -m <marker>`.
