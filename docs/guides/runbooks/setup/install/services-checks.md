# Optional Services And Checks

## Optional LLM Settings

LLM nodes are disabled unless `--llm` is passed. Configure the model with:

```bash
export CRK_MODEL=ollama:llama3.1
```

The self-hosted runtime supports Ollama. Codex and Claude Code can operate the
local stack through CLI or MCP, but they are agent hosts rather than CRK
runtime model providers. LLM output is never evidence; it must still pass
source support, packet review, validation, and privacy review.

## Optional Local Services

SearXNG source discovery:

```bash
cr-kit discover-sources data/cases/<case_slug> \
  --query "<public source search query>" \
  --searxng-url http://localhost:8080
```

Docling parse and OCR:

```bash
cr-kit parse-source data/cases/<case_slug> <SOURCE_ID>
cr-kit ocr-source data/cases/<case_slug> <SOURCE_ID>
```

Qdrant-backed local retrieval:

```bash
cr-kit index-case data/cases/<case_slug> \
  --qdrant-url http://localhost:6333

cr-kit query-case data/cases/<case_slug> \
  "Which claims lack source spans?"
```

Workflow memory:

```bash
cr-kit remember-research-actions data/cases/<case_slug> --provider local
```

Memory and retrieval results are operational context only. They are not
evidence and do not replace `source_ids`, `source_span_ids`, validation, or
public-output review.

## Public-Output Checklist

Before any report, script, evidence board, Manim export, or bundle leaves the
local workspace:

1. Run `validate`.
2. Run `report`.
3. Check source reliability grades and source independence.
4. Check contradictions, denials, corrections, retractions, and court findings.
5. Check `public_export`, `privacy_review`, `privacy_level`, and
   `living_status`.
6. Run `audit-public-export`, `audit-privacy-redactions`,
   `audit-source-independence`, or `review-narrative-readiness` when the case
   needs that review surface.
7. Keep private-person details, minors, addresses, contact details, medical
   details, and weak allegations out of public exports.

## Troubleshooting

| Symptom | Check |
|---|---|
| `ModuleNotFoundError: cli` | Run commands through `moon run crk:<task>` or `uv run --cache-dir .uv-cache --no-project --with-editable . -- python -m crime_research_kit._runtime.cli ...`. |
| `crk-ledger` not found | Run through `uv run --cache-dir .uv-cache --no-project --with-editable . -- crk-ledger ...` or install the package editable. |
| Case files appear in the wrong directory | Use `data/cases/<case_slug>` from the repository root. |
| LangGraph imports fail | Run with `uv run --cache-dir .uv-cache --no-project --with-editable '.[agentic]' -- ...`. |
| LLM node imports fail | Run with `uv run --cache-dir .uv-cache --no-project --with-editable '.[llm]' -- ...` and set `CRK_MODEL`. |
| Parse, OCR, retrieval, or memory commands fail | Install the matching optional extra and start any required local services. |
| A claim is blocked from public export | Keep it internal until source support, contradiction review, source-independence review, and privacy review are complete. |
