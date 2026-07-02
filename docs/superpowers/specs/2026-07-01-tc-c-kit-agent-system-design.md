# tc-c-kit Agent System: Ops Core, LangGraph Pipeline, MCP Server

Status: approved design, 2026-07-01
Scope: `tc-c-kit/` (case_builder package, `.agents/skills`, docs)

## Goal

Make the tc-c-kit agentic workflow and case-building system robust by layering
three consumers over one shared, safety-enforcing operations core:

- **Interactive**: an MCP server so Claude Code / Codex sessions drive case
  work through typed tools, guided by the existing `.agents/skills`.
- **Batch/autonomous**: the `case_builder` LangGraph app completes the full
  case-building loop with durable state, resumable human review gates, and
  bounded LLM agent nodes.
- **CLI**: the existing `cr-kit` CLI, re-pointed at the same core.

The CRK case folder (`data/cases/<slug>/records/*.jsonl`) remains the
canonical ledger. Nothing in this design changes the data model or the safety
contract in `docs/skill-api-spec.md`; it moves that contract into code.

## Decisions (from brainstorming)

| Question | Decision |
| --- | --- |
| Where does agent intelligence live? | Both layers: MCP for interactive hosts, LangGraph for batch runs, shared tool core underneath. |
| LLM provider | Self-hosted runtime provider. Ollama is supported now; future providers must expose local/self-hosted APIs. |
| MCP write authority | Read/query everything; writes limited to `staging/`; `import-extraction` gated behind an explicit `confirm` parameter. |
| Packaging | One phased roadmap spec (this document); implementation plans proceed phase by phase. |
| Internal architecture | Shared ops core (`case_builder/ops/`) consumed by CLI, graph, and MCP — not MCP-as-hub, not duplicate thin adapters. |

## Architecture

```text
┌─────────────┐  ┌──────────────────┐  ┌─────────────────┐
│  cli.py     │  │ LangGraph graph/ │  │ MCP server mcp/ │   frontends
└──────┬──────┘  └────────┬─────────┘  └────────┬────────┘
       └─────────────┬────┴─────────────────────┘
              ┌──────▼──────┐
              │   ops/      │  typed operations + safety policy      NEW
              └──────┬──────┘
    ┌────────┬───────┼────────┬──────────┐
 tcr.py   parsing/ retrieval/ memory/  acquisition/       existing
 (subprocess)                                             building blocks
```

### Component 1: `case_builder/ops/` — the operations core

Every case operation is a typed Python function returning a shared `OpResult`
(`ok: bool`, `data`, `errors`, `warnings`, plus the audit-ready command
record). The existing `tools/crk_cli.py` subprocess runner survives as the
low-level executor inside ops; `CrkToolResult` folds into `OpResult`. Over
time, subprocess calls may be replaced with direct imports without changing
the ops API.

Modules (each under the 200 non-comment LOC ceiling, each package with a
`README.md`, per repo convention):

| Module | Operations |
| --- | --- |
| `ops/case.py` | `init_case`, `case_info`, `validate`, `report` |
| `ops/sources.py` | `add_source`, `ingest_url`, `preserve_source`, `discover_sources`, `parse_source`, `ocr_source` |
| `ops/extraction.py` | `draft_extraction`, `list_packets`, `read_packet`, `save_packet`, `import_extraction(confirm=...)` |
| `ops/query.py` | ledger reads (records by type/ID/filter), retrieval `query_case`, `link_names` |
| `ops/exports.py` | manim, timeline, case charts, clusters, analysis charts, UFB bundle |
| `ops/review.py` | readiness / privacy / contradiction / independence audits, review-gate state |
| `ops/policy.py` | the safety contract as code (below) |

`ops/policy.py` enforces:

- **Write classification**: ops may write freely to `staging/` and `exports/`;
  canonical `records/*.jsonl` writes happen only through `import_extraction`
  and existing CRK commands, and `import_extraction` requires `confirm=True`.
- **Privacy filtering**: `public_export: false` records are excluded from any
  read or export surface unless `include_private` is explicitly passed; when
  it is, the result notes what was included.
- **Automation defaults**: records produced by automated paths get
  `status: unverified`, low confidence, `public_export: false`.
- **Guilt-label lint**: drafted packets are scanned for suspect/perpetrator/
  member/accomplice labels that lack a citing source and are rejected with a
  warning rather than saved.
- **Provider egress tagging**: when a non-local LLM provider is configured,
  runs are tagged in the audit log to record that source text left the machine.

Every op appends to `records/research_actions.jsonl` through the existing
audit mechanism, so agent activity and human activity share one audit trail.

**Interface contract**: frontends never touch `tcr.py`, the ledger files, or
the local-stack modules directly; they call ops. The safety contract therefore
has exactly one enforcement point.

### Component 2: LangGraph pipeline completion

The graph grows from the current 4-node bootstrap to the full loop, following
the node order already documented in `docs/case-builder-langgraph.md`:

```text
infer_lanes → init_case → plan_public_records
   → source_capture → parse_or_ocr → draft_extraction(LLM)
   → packet_review_gate [interrupt]
   → import_and_validate → index_case
   → readiness_audit(LLM-assisted) → export_review_gate [interrupt]
   → export_bundle
```

- **Durable state**: a SQLite checkpointer at
  `data/cases/<case>/.runs/checkpoints.db`. Runs survive restarts.
- **Real review gates**: `packet_review_gate` and `export_review_gate` use
  LangGraph `interrupt()`. Resume via
  `cr-kit resume <case> --thread <id> --approve packet:<SOURCE_ID>`
  (and `--reject` with a reason, which routes back to drafting or ends the
  branch). The sequential fallback runner keeps working for dependency-free
  dry runs by stopping at gates exactly as today.
- **Node behavior**: all nodes call ops; nodes never shell out or write files
  themselves. `merge_result` semantics (planned_commands, tool_results,
  errors, status) are preserved on top of `OpResult`.

### Component 3: LLM provider layer — `case_builder/llm/`

A single module exposing `get_chat_model()` driven by `CRK_MODEL` config
(env var or config file): `ollama:<model>` (default). The runtime path rejects
managed model-provider specs; future additions must expose self-hosted local
APIs. LangGraph nodes and any future callers share this provider layer.

### Component 4: Agent nodes (bounded LLM calls)

Agent nodes are single-purpose, structured-output LLM calls — not
free-roaming agents:

- **`draft_extraction`**: fills the CLI-generated packet template from parsed
  source text (chunked via the retrieval index when the source is long).
  Output must be schema-valid against `docs/schemas/`; automated records get
  `status: unverified`; the node never invents source IDs. Invalid output is
  retried once with the validation errors, then surfaced as a node error.
- **`readiness_audit`**: runs the deterministic audits via ops, then has the
  LLM summarize contradiction/privacy/independence findings into a reviewer
  brief. It flags; it never decides or edits records.
- **`lane_router`**: keyword policy in `agents/source_lanes.py` remains the
  deterministic base. An optional LLM pass may suggest additional lanes,
  recorded as suggestions with rationale — never silently applied.

### Component 5: MCP server — `case_builder/mcp/`

Built on the official Python MCP SDK (`FastMCP`), stdio transport, launched
via a new `crk-mcp` console script behind a `[mcp]` optional-dependency
extra. Tools are thin wrappers over ops; names mirror the ops API.

**Read/query tools (always available)**: `case_info`, `list_cases`,
`get_records` (record type + filters), `query_case` (retrieval),
`get_source_text`, `list_staged_packets`, `run_report`.

**Staged-write tools**: `discover_sources`, `ingest_url`, `add_source`,
`parse_source`, `ocr_source`, `draft_extraction`, `save_extraction_packet`
(schema-validated into `staging/`), `link_names`.

**Gated tools**: `import_extraction(case, packet, confirm: bool)` refuses
unless `confirm=true`, and its tool description instructs the model to obtain
explicit user approval first. `export_*` tools accept `include_private` but
default to public-safe and echo what was filtered.

**Resources** (read-only case context): `crk://cases/<slug>/case.json`,
`crk://cases/<slug>/records/<type>`,
`crk://cases/<slug>/staging/extractions/<id>`, plus the controlled
vocabularies and topic extraction templates from the skill references.

**Prompts**: `start_case`, `process_source`, `review_packet`,
`public_readiness` — so MCP hosts other than Codex/Claude Code receive the
workflow guidance in-band.

Every tool call logs through the ops audit path. No secrets or endpoint
config appear in tool results; Qdrant/SearXNG/LLM endpoints come from env.

### Component 6: Skills integration and vocabulary consolidation

- `truecrime-cult-research/SKILL.md` gains a "tool access" section: prefer
  MCP tools when the server is registered; fall back to `tcr.py` CLI
  otherwise. Operation names match in both surfaces.
- Adjacent skills reference shared op names for packet workflows instead of
  hand-written command lines, reducing drift between skill text and CLI flags.
- **`docs/lanes.json`** becomes the single source of truth for the lane
  vocabulary currently duplicated across `agents/source_lanes.py`, the
  `public-records-router` skill references, and `draft-extraction --template`
  names. Ops, the router policy, and skill reference docs all read or are
  generated from it.

## Error handling

- Ops return structured errors in `OpResult`; frontends render them (CLI:
  stderr + exit code; graph: `errors` list + `status: error`; MCP: tool error
  content). No frontend parses stdout.
- Agent-node LLM failures (invalid JSON, schema violations, missing source
  IDs) retry once with error feedback, then fail the node without writing to
  staging.
- Gated operations fail closed: missing `confirm`, failed validation, or a
  policy violation blocks the write and records why in the audit log.
- Interrupted graph runs are resumable from the checkpointer; a corrupted or
  missing checkpoint DB degrades to a fresh run with a warning, never a crash.

## Testing

- **Ops**: direct unit tests against `data/examples/synthetic_case` — no LLM,
  no network.
- **Graph**: sequential-runner tests with fake ops; interrupt/resume tests
  with the SQLite checkpointer in a temp dir.
- **Agent nodes**: golden-file tests with a stubbed chat model covering
  structured-output parsing, schema validation, and refusal on missing source
  IDs.
- **MCP**: in-process tests via the SDK client asserting the gating —
  `import_extraction` without `confirm` fails; `public_export: false` records
  never appear in default reads/exports.
- **Safety invariants as tests**: unverified-by-default on automated records,
  guilt-label lint, and privacy filtering each get explicit tests rather than
  living only in AGENTS.md prose.
- The existing 200-LOC structure test extends to `ops/`, `llm/`, and `mcp/`.

## Phased roadmap

Each phase is independently shippable, in order. Phases 2 and 4 both depend
only on Phase 1; MCP (Phase 4) may be pulled ahead of Phases 2–3 if
interactive value is wanted sooner.

1. **Ops core** — extract `ops/` + `OpResult` + `policy.py`; re-point CLI and
   existing graph nodes; port safety invariants to tests. Pure refactor plus
   hardening; no behavior change.
2. **Pipeline completion (deterministic)** — checkpointer, interrupt/resume,
   `source_capture`, `parse_or_ocr`, `import_and_validate`, `index_case`,
   `export_bundle` nodes.
3. **LLM layer + agent nodes** — `llm/` provider, `draft_extraction` agent,
   `readiness_audit` brief, `lane_router` suggestions.
4. **MCP server** — tools/resources/prompts over ops, gating tests,
   `crk-mcp` entry point, `[mcp]` extra.
5. **Skills + vocabulary consolidation** — `docs/lanes.json`, skill-doc
   updates, MCP registration docs for Claude Code/Codex.

## Out of scope

- Changes to the JSONL data model or JSON schemas.
- An HTTP/remote transport for the MCP server (stdio only for now).
- Autonomous web crawling beyond the existing SearXNG lead-only discovery.
- Multi-case orchestration or cross-case agents.
- Replacing `tcr.py`; it remains the canonical implementation wrapped by ops.

## Safety boundaries (unchanged, now enforced in code)

- No guilt, membership, motive, or participation inference from proximity.
- No suspect/perpetrator/member labels without a citing source.
- Automated records: `status: unverified`, low confidence,
  `public_export: false`.
- No canonical import without human review (`confirm` gate / graph
  interrupt).
- Private-person details redacted by default; public exports trace
  `claim → sources → reliability → confidence → privacy review`.
