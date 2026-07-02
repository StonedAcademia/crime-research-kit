# case_builder.ops

Typed operations core. Every case operation is a function returning `OpResult`;
frontends (CLI, LangGraph nodes, future MCP server) call these functions and
never touch `tcr.py`, the JSONL ledger, or local-stack modules directly.

| Module | Responsibility |
| --- | --- |
| `result.py` | `OpResult` dataclass and `local_op` wrapper for Python-native ops. |
| `runner.py` | `CrkRunner` subprocess executor around the repo-local `tcr.py`. |
| `policy.py` | Safety contract as code: staged-write classification, privacy filtering, automation defaults, guilt-label lint. |
| `case.py` | Case lifecycle: init, info, validate, report. |
| `sources.py` | Source intake: planning, registration, ingestion, preservation, discovery, parsing, OCR. |
| `extraction.py` | Extraction packets: drafting, staging reads/writes, gated canonical import. |
| `query.py` | Ledger reads with privacy filtering, retrieval index/query, name linking. |
| `review.py` | Deterministic audits: contradictions, narrative readiness, privacy, public export, source independence. |
| `exports.py` | Public-safe-by-default export commands. |

The safety contract (`docs/guides/skill-api-spec.md`) is enforced here,
once, so the frontends cannot disagree about what is gated.
