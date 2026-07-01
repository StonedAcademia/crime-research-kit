# LangGraph Case Builder

This design keeps the TRCR case folder as the source of truth and uses
LangGraph only as an orchestration runtime. Agents and graph nodes may draft
plans, extraction packets, and audits, but canonical records are written only by
the existing TRCR import and validation commands.

## Ownership

| Layer | Owner | Notes |
| --- | --- | --- |
| Case ledger | `data/cases/<case>/records/*.jsonl` | Canonical source, entity, event, claim, relationship, quote, redaction, and action records. |
| Workflow state | `case_builder.CaseBuilderState` | Serializable run state for planning, command outputs, errors, and review gates. |
| Orchestration | LangGraph | Optional runtime for resumable step graphs. The sequential runner remains available for tests and local dry runs. |
| Observability | LangSmith | Enabled by environment variables; do not send private source text or unredacted private-person details. |
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

## Bootstrap Workflow

```text
infer_lanes
  -> init_case
  -> plan_public_records
  -> review_gate
```

The first slice intentionally stops at a human review gate. Later slices should
add source capture, extraction drafting, import, validation, bundle export, and
Apothecary handoff as separate nodes with the same rule: source-backed drafts
must be reviewed before `import-extraction`.

## Running Locally

Dry run with no optional dependencies:

```bash
PYTHONPATH=src python -m case_builder.cli plan data/cases/example_case \
  --title "Example Case" \
  --subject "Jane Doe missing person last seen near Riverside Park map"
```

Execute the TRCR commands:

```bash
PYTHONPATH=src python -m case_builder.cli plan data/cases/example_case \
  --title "Example Case" \
  --subject "Jane Doe missing person last seen near Riverside Park map" \
  --execute
```

Use LangGraph explicitly:

```bash
pip install -e '.[agentic]'
trcr-case-builder plan data/cases/example_case \
  --title "Example Case" \
  --subject "Jane Doe missing person last seen near Riverside Park map" \
  --runner langgraph
```

Enable LangSmith tracing in development or staging:

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=<redacted>
export LANGSMITH_PROJECT=trcr-case-builder-dev
```

## Safety Boundaries

- Do not let graph nodes infer guilt, motive, cult membership, suspect status, or
  hidden control from proximity.
- Do not publish private addresses, private contact details, school/workplace
  details, family-member details, medical details, or minor-sensitive details.
- Do not import extraction packets without human review.
- Record every workflow action and command result in local run state before
  writing canonical records.
- Treat LangSmith traces as operational metadata, not evidence.

## Next Nodes

Recommended next implementation order:

1. `source_capture`: wraps `add-source`, `ingest-url`, and `preserve-source`.
2. `draft_extraction`: wraps `draft-extraction` and calls a bounded packet
   drafting agent.
3. `human_packet_review`: blocks import until the packet is approved.
4. `import_and_validate`: wraps `import-extraction` and `validate`.
5. `readiness_audit`: wraps narrative, privacy, contradiction, and
   source-independence checks.
6. `export_bundle`: exports Phanestead-readable bundles for Apothecary.

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
