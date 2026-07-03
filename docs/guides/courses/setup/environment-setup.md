# Setting Up The Environment

This guide prepares a local case workspace after CRK is installed.

## Choose A Case Directory

Case workspaces live under ignored `data/cases/` paths. For the sample course:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger init-case \
  data/cases/mkultra_course \
  --title "MKUltra Source-Traceable Course Case"
```

Expected layout:

```text
data/cases/<case>/
  raw/downloads/
  raw/sources/
  records/
  staging/extractions/
  exports/
```

Keep raw PDFs, HTML captures, extracted text, staged packets, generated charts,
and exports in the case workspace unless a maintainer explicitly asks for a
fixture.

## Pick Optional Extras

Install only the extras needed for the surface you are using:

| Extra | Use |
| --- | --- |
| `.[dev]` | Tests and course validation. |
| `.[mcp]` | MCP server usage from Claude Code or another MCP host. |
| `.[documents]` | OCR and document parsing workflows. |
| `.[retrieval]` | Local retrieval/indexing workflows. |
| `.[agentic]` | LangGraph-style planning, checkpoints, and resume flows. |
| `.[governance]` | Audit, release, SBOM, and policy checks. |

Example:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[documents]' \
  -- cr-kit ocr-source data/cases/mkultra_course S_SOURCE_ID
```

## Configure Local Services

SearXNG, Qdrant, Ollama, OCRmyPDF, and memory providers are optional. They help
with discovery, retrieval, OCR, local model use, and workflow memory. They do
not change the evidence rule:

```text
public point -> source ID -> locator -> reliability grade -> status -> review
```

LLM output is never evidence. It can suggest extraction candidates only.

## Source Storage Rules

| Source State | Storage | Handling |
| --- | --- | --- |
| Reachable PDF or HTML | `raw/downloads/` plus text in `raw/sources/` | Can support claims after locator review. |
| Image-only scan | Raw file plus OCR output or OCR-needed marker | Do not cite exact text until OCR succeeds. |
| HTTP blocked or redirect loop | Source metadata only | Use as a lead; do not support facts. |
| Testimony | Captured source plus speaker context | Extract as testimony, not established fact. |
| Boundary record | Captured source with narrow purpose | Use only for what it directly supports. |

## Done When

- The case directory exists under `data/cases/`.
- Optional extras are chosen for your workflow.
- Raw and extracted-source storage rules are clear before capture starts.
