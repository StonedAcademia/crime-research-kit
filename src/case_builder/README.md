# case_builder

`case_builder` is a small agent app for bootstrapping TRCR case work. It keeps
the JSONL case ledger canonical and routes case operations through the shared
ops core. The public API is `CaseBuilderState`, `new_run_id`, and
`run_case_builder`.

## Module map

| Package | Responsibility |
| --- | --- |
| `agents/` | Deterministic routing policy such as source-lane inference. |
| `app/` | Service boundary and runner selection. |
| `graph/` | LangGraph state, nodes, graph builder, and sequential fallback. |
| `lanes/` | Canonical lane/template registry loader over `docs/registry/`. |
| `models/` | Serializable state models shared by CLI, graph, and tests. |
| `ops/` | Typed operations core: `OpResult`, `TrcrRunner`, safety `policy`, and per-domain op modules. Frontends call ops instead of `tcr.py` or the ledger. |
| `acquisition/` | Local source discovery helpers. |
| `parsing/` | Local Docling and OCRmyPDF wrappers for registered source artifacts. |
| `retrieval/` | Rebuildable LlamaIndex/Qdrant evidence indexing over records and source text. |
| `memory/` | Workflow memory providers for decisions, dead ends, and unresolved questions. |
