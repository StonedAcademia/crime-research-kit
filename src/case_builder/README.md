# case_builder

`case_builder` is a small agent app for bootstrapping CRK case work. It keeps
the JSONL case ledger canonical and routes case operations through grouped
core, pipeline, and adapter packages. The public API is `CaseBuilderState`,
`new_run_id`, and `run_case_builder`.

## Module map

| Package | Responsibility |
| --- | --- |
| `core/` | Case ledger helpers, configuration, lane registry, state models, and workflow memory. |
| `pipeline/` | Deterministic agents, service boundary, and LangGraph/sequential workflow execution. |
| `adapters/io/` | Local source discovery, parsing/OCR, and rebuildable evidence retrieval indexes. |
| `adapters/ops/` | Typed operations, runner/result contracts, and safety policy shared by frontends. |
| `adapters/interfaces/` | LLM and MCP interface adapters that call ops instead of touching ledger internals. |
