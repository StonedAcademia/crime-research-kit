# case_builder.mcp

MCP server over the ops core (stdio, `trcr-mcp`). Tool logic lives in plain
handler functions (`*_tool(ctx, ...)`) so tests call them directly; each
module's `register(mcp, ctx)` wraps them in typed closures for FastMCP schema
generation.

| Module | Responsibility |
| --- | --- |
| `context.py` | `ServerContext`, slug-validated `resolve_case`, uniform `error_dict`. |
| `tools_read.py` | Read/query tier: case info, records, source text, retrieval, packets, report. |
| `tools_write.py` | Staged-write tier: discovery, ingestion, parsing, drafting, packet save, name linking. |
| `tools_gated.py` | Gated tier: `import_extraction` (requires `confirm=true`), public-safe-by-default exports. |
| `resources.py` | `trcr://cases/...` and `trcr://references/...` read-only resources. |
| `prompts.py` | Workflow prompts: start_case, process_source, review_packet, public_readiness. |
| `server.py` | `create_server()` and `main()` stdio entry point. |

The safety contract is enforced in `case_builder.ops`: this package adds no
second enforcement path and must never call `tcr.py` or the ledger directly.
Config: `TRCR_CASES_ROOT` (default `<repo>/data/cases`).
Skill references: `TRCR_SKILL_ROOT` (default repo-local `.agents` skill copy).
