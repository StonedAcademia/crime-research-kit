# Test Layout

Tests are grouped by the kind of confidence they provide.

| Directory | Purpose | Typical command |
| --- | --- | --- |
| `runtime/unit/` | Pure functions, small policy helpers, parser/model behavior without full workflow orchestration. | `.venv/bin/python -m pytest tests/runtime/unit -v` |
| `runtime/integration/` | Ops, CLI-adjacent, filesystem, source ledger, export, and component-boundary tests. | `.venv/bin/python -m pytest tests/runtime/integration -v` |
| `runtime/e2e/` | End-to-end orchestration through graph, service, or MCP session boundaries. Optional extras may skip tests. | `.venv/bin/python -m pytest tests/runtime/e2e -v` |
| `quality/governance/` | Repository policy, schemas, generated docs, lane registry, and skill-doc drift checks. | `.venv/bin/python -m pytest tests/quality/governance -v` |
| `quality/smoke/` | Fast heartbeat checks for the main case-builder path. | `.venv/bin/python -m pytest tests/quality/smoke -v` |

`tests/conftest.py` automatically marks tests with the marker matching the
nearest known category in the path, so `-m unit`, `-m integration`, `-m e2e`,
`-m governance`, and `-m smoke` also work.
