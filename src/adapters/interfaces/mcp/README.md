# MCP Interface Adapters

MCP server for `crk-mcp`. SDK-backed tools are registered through the SDK
operation catalog where the catalog can safely provide operation names, safety
tiers, and adapter metadata. `tools/registry.py` binds catalog entries to local
tool handlers and records direct exceptions. Tool logic still lives in plain
handler functions (`*_tool(ctx, ...)`) so tests call handlers directly; each
module's `register(mcp, ctx)` wraps those handlers in typed closures for
FastMCP schema generation.

Prompts and resources remain explicit MCP content, not SDK catalog output.
They describe host guidance and `crk://` resource views rather than SDK
operations. `run_report` is also a direct runtime-owned exception until the
evidence-board report has explicit public/private filtering semantics.

| Module | Responsibility |
| --- | --- |
| `context.py` | `ServerContext`, slug-validated `resolve_case`, uniform `error_dict`. |
| `tools/registry.py` | Catalog-backed MCP tool metadata plus explicit direct-tool exceptions. |
| `tools/read.py` | Read/query tier: case info, records, source text, retrieval, packets, and the direct `run_report` exception. |
| `tools/write.py` | Staged-write tier: discovery, ingestion, parsing, drafting, packet save, name linking. |
| `tools/gated.py` | Gated tier: `import_extraction` (requires `confirm=true`), public-safe-by-default exports. |
| `content/resources.py` | Explicit `crk://cases/...` and `crk://references/...` read-only resources. |
| `content/prompts.py` | Explicit workflow prompts: start_case, process_source, review_packet, public_readiness. |
| `server.py` | `create_server()` and `main()` stdio entry point. |

The safety contract is enforced by SDK/runtime operations: this package adds
no second enforcement path and must never call `crk-ledger` or the ledger
directly. Config: `CRK_CASES_ROOT` (default `<repo>/data/cases`).
Skill references: `CRK_SKILL_ROOT` (default repo-local `.agents` skill copy).
