# Initial App Install

This runbook sets up the TRCR kit and the optional case-builder app for local
case work. Commands assume you are running from the `tc-c-kit` repository root:

```text
<project_root>/
```

That keeps the repo-local skill path at
`.agents/skills/truecrime-cult-research/` and keeps generated case work under
`data/cases/`.

## Prerequisites

- Python 3.10 or newer.
- A shell with `python3` and `pip`.
- `proto` for the preferred cross-platform task workflow. `moon`, Python, and
  Bun are pinned in `.prototools` and installed through proto.
- Optional: `bun` for Phanestead UFB bundle exports.
- Optional local services: SearXNG for source discovery and Qdrant for local
  retrieval or memory.
- Optional system packages for OCR: Tesseract and Ghostscript, used by
  OCRmyPDF.

## Install the Core Kit

Install proto first.

Linux, macOS, or WSL:

```bash
curl -fsSL https://moonrepo.dev/install/proto.sh | bash
```

Windows PowerShell:

```powershell
irm https://moonrepo.dev/install/proto.ps1 | iex
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then install the pinned proto toolchain and run the moon install task from the
repository root:

```bash
proto install
moon run trcr:install-dev
```

`moon run trcr:install-dev` uses `deployment/scripts/tools/install.py` to create
`.venv`, upgrade pip, and install the package in editable mode with the `dev`
extra.

For a minimum runtime install without dev dependencies:

```bash
moon run trcr:install
```

The Makefile remains as a compatibility wrapper:

```bash
make install
make install-dev
make install-windows
```

All three route through moon; `install-windows` is an alias for the same
cross-platform installer rather than a separate PowerShell implementation.

Manual fallback without moon:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

The minimum install uses the core package only. The `dev` extra installs the
dependencies used by tests, schema validation, source extraction helpers, and
chart exports.

Use `.agents/...` for the skill script and `data/cases/...` for case paths.

## Optional Extras

Install only the surfaces you need:

```bash
python -m pip install -e '.[agentic]'
python -m pip install -e '.[llm]'
python -m pip install -e '.[mcp]'
python -m pip install -e '.[web-local]'
python -m pip install -e '.[documents]'
python -m pip install -e '.[retrieval]'
python -m pip install -e '.[memory-local]'
```

Use `agentic` for the LangGraph runner, `llm` for optional LLM packet helpers,
`mcp` for MCP frontends, `web-local` for local source discovery helpers,
`documents` for parsing and OCR, `retrieval` for local Qdrant/LlamaIndex
search, and `memory-local` for workflow memory.

## Self-Hosted Container Install

The container deployment treats those runtime surfaces as mandatory and runs
them with local services: SearXNG, Valkey, Qdrant, Ollama, OCR tooling,
retrieval, memory, LangGraph, and MCP.

```bash
cp deployment/.env.example deployment/.env
moon run trcr:docker-build
moon run trcr:docker-up
moon run trcr:docker-pull-model
moon run trcr:docker-smoke
```

Codex and Claude Code can operate the self-hosted stack through CLI or MCP.
They are agent hosts, not TRCR runtime model providers. No LangSmith, managed
vector store, or managed model-provider configuration is part of this
deployment. See `deployment/README.md`.

## Verify the Install

Run the synthetic fixture through the core validator:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate data/examples/synthetic_case
```

Check that the case-builder app can plan a dry run:

```bash
PYTHONPATH=src python -m case_builder.cli plan data/cases/install_smoke \
  --title "Install Smoke Test" \
  --subject "Synthetic public-source smoke test for setup verification"
```

If the package entry point is installed, the same app is available as:

```bash
trcr-case-builder plan data/cases/install_smoke \
  --title "Install Smoke Test" \
  --subject "Synthetic public-source smoke test for setup verification"
```

The dry-run planner records intended operations in JSON output. Add `--execute`
only when you want the app to create or modify the case workspace.

## Create the First Case

Initialize a local case workspace:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py init-case data/cases/<case_slug> \
  --title "<Case Title>"
```

Register a source manually when it should be tracked before extraction:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py add-source data/cases/<case_slug> \
  --title "<Source Title>" \
  --url "<URL or local path>" \
  --source-type news_article \
  --reliability-grade B \
  --notes "Initial source registration"
```

Or capture a public URL directly:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py ingest-url data/cases/<case_slug> \
  "<URL>" \
  --source-type news_article \
  --reliability-grade B
```

Draft an extraction packet for review:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction data/cases/<case_slug> <SOURCE_ID>
```

After the packet is filled and reviewed, import and validate it:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction data/cases/<case_slug> \
  data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json

python .agents/skills/truecrime-cult-research/scripts/tcr.py validate data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py report data/cases/<case_slug>
```

## Run the Case-Builder App

The case-builder app wraps the same ledger operations in a resumable workflow.
The ledger under `records/*.jsonl` remains the source of truth.

Dry run:

```bash
trcr-case-builder plan data/cases/<case_slug> \
  --title "<Case Title>" \
  --subject "<case subject, source question, names, dates, and places>"
```

Execute deterministic commands:

```bash
trcr-case-builder plan data/cases/<case_slug> \
  --title "<Case Title>" \
  --subject "<case subject, source question, names, dates, and places>" \
  --execute
```

Run with LangGraph checkpoints:

```bash
trcr-case-builder plan data/cases/<case_slug> \
  --title "<Case Title>" \
  --subject "<case subject, source question, names, dates, and places>" \
  --runner langgraph \
  --checkpoint \
  --execute
```

Resume after human packet review:

```bash
trcr-case-builder resume data/cases/<case_slug> \
  --thread <thread_id> \
  --approve-packet <SOURCE_ID>_extraction.json \
  --execute
```

Resume after public-export review:

```bash
trcr-case-builder resume data/cases/<case_slug> \
  --thread <thread_id> \
  --approve-export \
  --execute
```

## Optional LLM Settings

LLM nodes are disabled unless `--llm` is passed. Configure the model with:

```bash
export TRCR_MODEL=ollama:llama3.1
```

The self-hosted runtime supports Ollama. Codex and Claude Code can operate the
local stack through CLI or MCP, but they are agent hosts rather than TRCR
runtime model providers. LLM output is never evidence; it must still pass
source support, packet review, validation, and privacy review.

## Optional Local Services

SearXNG source discovery:

```bash
trcr-case-builder discover-sources data/cases/<case_slug> \
  --query "<public source search query>" \
  --searxng-url http://localhost:8080
```

Docling parse and OCR:

```bash
trcr-case-builder parse-source data/cases/<case_slug> <SOURCE_ID>
trcr-case-builder ocr-source data/cases/<case_slug> <SOURCE_ID>
```

Qdrant-backed local retrieval:

```bash
trcr-case-builder index-case data/cases/<case_slug> \
  --qdrant-url http://localhost:6333

trcr-case-builder query-case data/cases/<case_slug> \
  "Which claims lack source spans?"
```

Workflow memory:

```bash
trcr-case-builder remember-research-actions data/cases/<case_slug> --provider local
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
| --- | --- |
| `ModuleNotFoundError: case_builder` | Run `moon run trcr:install-dev`, activate `.venv`, or run with `PYTHONPATH=src`. |
| `.agents/.../tcr.py` not found | Run from the `tc-c-kit` repository root. |
| Case files appear in the wrong directory | Use `data/cases/<case_slug>` from the repository root. |
| LangGraph imports fail | Install `python -m pip install -e '.[agentic]'` inside `.venv`. |
| LLM node imports fail | Install `python -m pip install -e '.[llm]'` inside `.venv` and set `TRCR_MODEL`. |
| Parse, OCR, retrieval, or memory commands fail | Install the matching optional extra and start any required local services. |
| A claim is blocked from public export | Keep it internal until source support, contradiction review, source-independence review, and privacy review are complete. |
