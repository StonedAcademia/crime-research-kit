# LangGraph Case Builder

This design keeps the CRK case folder as the source of truth and uses
LangGraph only as an orchestration runtime. Agents and graph nodes may draft
plans, extraction packets, and audits, but canonical records are written only by
the existing CRK import and validation commands.

## Ownership

| Layer | Owner | Notes |
| --- | --- | --- |
| Case ledger | `data/cases/<case>/records/*.jsonl` | Canonical source, entity, event, claim, relationship, quote, redaction, and action records. |
| Workflow state | `case_builder.CaseBuilderState` | Serializable run state for planning, command outputs, errors, and review gates. |
| Orchestration | LangGraph | Optional runtime for resumable step graphs. The sequential runner remains available for tests and local dry runs. |
| Observability | Local logs and `research_actions.jsonl` | No managed tracing service is configured for the self-hosted stack. |
| Analysis surface | Phanestead Apothecary | Consumes exported bundles and reports readiness, source quality, timelines, and graph metrics. |

## Source Layout

| Directory | Responsibility |
| --- | --- |
| `src/case_builder/app/` | Use-case boundary and runner selection. |
| `src/case_builder/agents/` | Deterministic agent policy such as source-lane routing. |
| `src/case_builder/graph/` | LangGraph state, nodes, graph builder, and sequential fallback. |
| `src/case_builder/models/` | Serializable state models shared by CLI, graph, and tests. |
| `src/case_builder/ops/` | Typed operations core and safety policy shared by CLI, graph nodes, and future MCP frontends. |
| `src/case_builder/acquisition/` | Local source discovery helpers, currently SearXNG candidate reports. |
| `src/case_builder/parsing/` | Local Docling and OCRmyPDF wrappers for registered source artifacts. |
| `src/case_builder/retrieval/` | Rebuildable LlamaIndex/Qdrant evidence indexing over records and source text. |
| `src/case_builder/memory/` | Local workflow memory providers for decisions, dead ends, and unresolved questions. |

Each package directory has a local `README.md`. Python modules are kept under
200 non-comment LOC and checked by `tests/test_case_builder_structure.py`.

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
PYTHONPATH=src python -m case_builder.cli plan data/cases/example_case \
  --title "Example Case" \
  --subject "Jane Doe missing person last seen near Riverside Park map"
```

Execute the CRK commands:

```bash
PYTHONPATH=src python -m case_builder.cli plan data/cases/example_case \
  --title "Example Case" \
  --subject "Jane Doe missing person last seen near Riverside Park map" \
  --execute
```

Use LangGraph explicitly:

```bash
pip install -e '.[agentic]'
cr-kit plan data/cases/example_case \
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
environment variable (`provider:model`, default `ollama:llama3.1`; install
`pip install -e '.[llm]'`). The self-hosted deployment supports Ollama as the
runtime provider.

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
