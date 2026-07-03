# LangGraph Case Builder

This design keeps the CRK case folder as the source of truth and uses
LangGraph only as an orchestration runtime. Agents and graph nodes may draft
plans, extraction packets, and audits, but canonical records are written only by
the existing CRK import and validation commands.

The public workflow API is `crime_research_kit.sdk.WorkflowClient` through
`CrkClient().workflows`. CLI users reach the same boundary through `cr-kit plan`
and `cr-kit resume`. The `pipeline.*` modules, graph nodes, and app service are
private runtime internals, not Python SDK imports.

## Ownership

| Layer | Owner | Notes |
| --- | --- | --- |
| Case ledger | `data/cases/<case>/records/*.jsonl` | Canonical source, entity, event, claim, relationship, quote, redaction, and action records. |
| Public workflow SDK | `crime_research_kit.sdk.WorkflowClient` | Public Python facade for plan/resume requests and `OperationResult` responses. |
| CLI adapter | `cr-kit plan` / `cr-kit resume` | Command surface over the SDK workflow facade. |
| Workflow state | `core.models.state.CaseBuilderState` | Serializable run state for planning, command outputs, errors, and review gates. |
| Orchestration | LangGraph | Optional runtime for resumable step graphs. The sequential runner remains available for tests and local dry runs. |
| Observability | Local logs and `research_actions.jsonl` | No managed tracing service is configured for the self-hosted stack. |
| Analysis surface | Phanestead Apothecary | Consumes exported bundles and reports readiness, source quality, timelines, and graph metrics. |

## Source Layout

| Directory | Responsibility |
| --- | --- |
| `src/core/` | Case ledger helpers, configuration, lane registry, state models, and workflow memory. |
| `src/crime_research_kit/sdk/` | Public SDK facade, result envelope, context, and workflow request/response boundary. |
| `src/pipeline/` | Deterministic agents, service boundary, and LangGraph/sequential workflow execution. |
| `src/adapters/io/` | Local source discovery, parsing/OCR, and rebuildable evidence retrieval indexes. |
| `src/adapters/ops/` | Typed operations, runner/result contracts, and safety policy shared by frontends. |
| `src/adapters/interfaces/` | CLI, LLM, and MCP interface adapters. CLI/MCP call SDK facades where operations are promoted. |

Each package directory has a local `README.md`. Python modules are kept under
200 non-comment LOC by `tests/quality/governance/test_repository_shape.py`.

## Pipeline Workflow

```text
infer_lanes -> suggest_lanes -> init_case -> plan_public_records
  -> source_capture -> parse_or_ocr -> draft_packets
  -> fill_packets
  -> packet_review_gate [interrupt]
  -> import_and_validate -> index_case -> readiness_audit
  -> readiness_brief
  -> export_review_gate [interrupt]
  -> export_bundle
```

Gates pause the run. Under LangGraph with `--checkpoint`, gates call
`interrupt()` and the run is resumable; in the sequential runner (and
non-checkpointed graphs) an unapproved gate ends the run with
`status: waiting_for_human_review`. Canonical import always flows through
`import_extraction(confirm=True)` downstream of the packet gate.

Checkpointed run and resume:

Python callers use the SDK facade:

```python
from crime_research_kit.sdk import CrkClient, CrkContext

client = CrkClient(CrkContext(repo_root=".", cases_root="data/cases"))
plan = client.workflows.plan(
    "example_case",
    title="Example Case",
    subject="Jane Doe missing person",
    runner="langgraph",
    checkpoint=True,
)
```

CLI callers use the adapter surface:

```bash
cr-kit plan data/cases/example_case \
  --title "Example Case" --subject "Jane Doe missing person" \
  --source-url "https://example.com/story" \
  --runner langgraph --checkpoint --execute

cr-kit resume data/cases/example_case --thread <thread_id> \
  --approve-packet S0001_extraction.json --execute

cr-kit resume data/cases/example_case --thread <thread_id> \
  --approve-export --execute
```

Checkpoints persist in `data/cases/<case>/.runs/checkpoints.db`.

## Running Locally

Dry run with no optional dependencies:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- python -m cli plan data/cases/example_case \
  --title "Example Case" \
  --subject "Jane Doe missing person last seen near Riverside Park map"
```

Execute the CRK commands:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- python -m cli plan data/cases/example_case \
  --title "Example Case" \
  --subject "Jane Doe missing person last seen near Riverside Park map" \
  --execute
```

Use LangGraph explicitly:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[agentic]' -- cr-kit plan data/cases/example_case \
  --title "Example Case" \
  --subject "Jane Doe missing person last seen near Riverside Park map" \
  --runner langgraph
```

## Safety Boundaries

- Do not let graph nodes infer guilt, motive, cult membership, suspect status, or
  hidden control from proximity.
- Do not publish private addresses, private contact details, school/workplace
  details, family-member details, medical details, or minor-sensitive details.
- Do not import extraction packets without human review.
- Record every workflow action and command result in local run state before
  writing canonical records.

## LLM Agent Nodes

Optional nodes activate with `--llm` (plus `--execute`) and the `CRK_MODEL`
environment variable (`provider:model`, default `ollama:llama3.1`; sync with
`uv run --cache-dir .uv-cache --no-project --with-editable '.[llm]' -- ...`).
The self-hosted deployment supports Ollama as the runtime provider.

- `suggest_lanes`: lane suggestions with rationale, recorded in
  `lane_suggestions`; never silently applied.
- `fill_packets`: fills CLI-drafted extraction packets from parsed source
  text. Output must be JSON matching the template, cite only the packet's
  source ID, and pass the guilt-label lint; assertion records are forced to
  `status: unverified`, capped confidence, `public_export: false`. One retry
  with error feedback, then the failure is recorded and the packet is left
  unfilled for a human.
- `readiness_brief`: summarizes the deterministic audit outputs into
  `staging/candidates/readiness_brief_<date>.md`. It flags; it never decides.

LLM output is never evidence; filled packets still stop at the packet review
gate.

## Local Stack Commands

The optional local stack keeps all non-web services under user control:

- `discover-sources`: queries a local SearXNG instance and writes lead-only
  source candidates under `staging/candidates/`.
- `parse-source`: runs Docling against a registered source `raw_path`, writes a
  text artifact under `raw/sources/`, and updates the source `text_path`.
- `ocr-source`: runs OCRmyPDF/Tesseract against a registered PDF source and
  updates the source `text_path` to the OCR sidecar.
- `index-case`: builds a local Qdrant-backed LlamaIndex evidence index from
  source text and canonical JSONL records.
- `query-case`: runs local retrieval against the same evidence index.
- `remember-research-actions`: stores recent workflow actions in either
  case-local JSONL memory or Mem0 OSS configured for local Qdrant/local models.

Memory rows and retrieval hits are not evidence. They can guide extraction and
review, but public claims still need source records, source spans when
appropriate, validation, and privacy/source-independence review.
