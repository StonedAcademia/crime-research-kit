# Lesson 4: Tested Full-Stack Workflow

This lesson mirrors the opt-in live E2E suite for the MKULTRA course. The
automated tests use a temporary case workspace so local course work under
`data/cases/mkultra_course` is not changed. The manual commands below use the
real course case when an operator wants to build the lesson artifacts locally.

## Automated Run

Start the local services you want to cover:

```bash
docker compose --env-file deployment/.env.example -f deployment/docker-compose.yml up -d qdrant searxng searxng-valkey ollama
```

Pull the Ollama model if the LLM lane is part of the run:

```bash
moon run crk:docker-pull-model
```

Run the curated live workflow:

```bash
export CRK_LIVE_MKULTRA=1
export CRK_SEARXNG_URL=http://127.0.0.1:18080
export CRK_QDRANT_URL=http://127.0.0.1:6333
export OLLAMA_HOST=http://127.0.0.1:11434
export CRK_MODEL=ollama:llama3.1

moon run crk:test-mkultra-live
```

Run just the CLI, MCP, and agent/skill surface acceptance path:

```bash
export CRK_LIVE_MKULTRA=1
export CRK_LIVE_CODEX=1
export CRK_CODEX_BIN=codex

moon run crk:test-mkultra-surfaces
```

The Codex host lane is separate and uses the Codex service directly through
`codex exec`, not `CRK_MODEL` and not the OpenAI API:

```bash
export CRK_LIVE_CODEX=1
export CRK_CODEX_BIN=codex

moon run crk:test-mkultra-live
```

The suite covers a curated subset from `sources/manifest.json`:

| Source ID | Workflow Purpose |
| --- | --- |
| `S_NSARCHIVE_MKULTRA_CONTEXT_2024` | HTML capture, extraction packet, reviewed import, reports, audits, retrieval. |
| `S_CIA_MKULTRA_IG_1963` | Official PDF download, Docling/RapidOCR parse, and OCRmyPDF smoke when `tesseract` is on `PATH`. |
| `S_FBI_FINDERS_PART_01` | FBI Vault boundary record; direct live capture may become metadata-only when the endpoint returns an anti-bot challenge. |
| `S_FBI_JONESTOWN_HISTORY` | Boundary-source capture without treating it as an MKULTRA relationship. |

Expected artifacts in the temp case include source ledger rows, raw downloads,
text sidecars, source-preservation reports, staged extraction packets, a
reviewed canonical packet, name-link research brief, evidence-board Markdown,
internal visuals, timeline/corroboration CSVs, Qdrant query output, an Ollama
readiness brief, an optional Codex reviewer brief, and a surface-acceptance
transcript covering CLI, MCP, and agent/skill operation.

LLM and Codex outputs are candidate review material only. They are not evidence
and do not replace source IDs, source spans, validation, contradiction review,
privacy review, or human approval before canonical import.

## Manual Course Run

Use the same flow against the ignored course case when building lesson assets:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger init-case data/cases/mkultra_course \
  --title "MKUltra Source-Traceable Course Case"
```

Register or capture the curated sources from `sources/manifest.json`, then
preserve each captured source:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger preserve-source data/cases/mkultra_course S_NSARCHIVE_MKULTRA_CONTEXT_2024
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger preserve-source data/cases/mkultra_course S_CIA_MKULTRA_IG_1963
```

Parse or OCR local files after the raw paths exist:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[documents]' -- \
  cr-kit parse-source data/cases/mkultra_course S_CIA_MKULTRA_IG_1963
uv run --cache-dir .uv-cache --no-project --with-editable '.[documents]' -- \
  cr-kit ocr-source data/cases/mkultra_course S_CIA_MKULTRA_IG_1963
```

Draft packets and keep them staged until reviewed:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger draft-extraction \
  data/cases/mkultra_course S_NSARCHIVE_MKULTRA_CONTEXT_2024
```

After human review, import only the approved packet:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger import-extraction \
  data/cases/mkultra_course \
  data/cases/mkultra_course/staging/extractions/S_NSARCHIVE_MKULTRA_CONTEXT_2024_extraction.json
```

Link names neutrally and run review gates:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger link-names data/cases/mkultra_course \
  --name "National Security Archive|NSA" \
  --name "MKULTRA|Project MKULTRA|MK-ULTRA"

uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger validate data/cases/mkultra_course
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger audit-contradictions data/cases/mkultra_course
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger audit-source-independence data/cases/mkultra_course
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger audit-privacy-redactions data/cases/mkultra_course --warn-only
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger review-narrative-readiness data/cases/mkultra_course
```

Build public-safe exports after review:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger report data/cases/mkultra_course
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger export-case-visuals data/cases/mkultra_course --include-private
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger export-timeline data/cases/mkultra_course --include-private
```

Index and query with Qdrant plus HuggingFace embeddings:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[retrieval]' -- \
  cr-kit index-case data/cases/mkultra_course \
  --qdrant-url "$CRK_QDRANT_URL" \
  --embed-model "${CRK_EMBED_MODEL:-BAAI/bge-small-en-v1.5}"

uv run --cache-dir .uv-cache --no-project --with-editable '.[retrieval]' -- \
  cr-kit query-case data/cases/mkultra_course \
  "What does the National Security Archive source say about CIA behavior-control experiments?" \
  --qdrant-url "$CRK_QDRANT_URL" \
  --embed-model "${CRK_EMBED_MODEL:-BAAI/bge-small-en-v1.5}"
```

For MCP hosts, register `crk-mcp` as shown in
[Lesson 3](03-agent-workflows.md#use-crk-through-mcp), then run the same
staged workflow through `case_info`, `get_source_text`, `draft_extraction`,
`save_extraction_packet`, `link_names`, and gated `import_extraction`.
