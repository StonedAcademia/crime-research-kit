# Initial App Install

This runbook sets up the TRCR kit and the optional case-builder app for local
case work. Commands assume you are running from the wrapper repository root:

```text
/home/jdean/Documents/programming/true-crime-research
```

That keeps the repo-local skill path at
`.agents/skills/truecrime-cult-research/` and keeps generated case work under
`tc-c-kit/data/cases/`.

## Prerequisites

- Python 3.10 or newer.
- A shell with `python3` and `pip`.
- Optional: `bun` for Phanestead UFB bundle exports.
- Optional local services: SearXNG for source discovery and Qdrant for local
  retrieval or memory.
- Optional system packages for OCR: Tesseract and Ghostscript, used by
  OCRmyPDF.

## Install the Core Kit

For the minimum local app install, use the Makefile from inside `tc-c-kit`:

```bash
cd tc-c-kit
make install
```

`make install` detects Linux or Windows, verifies Python 3.10 or newer, creates
`.venv`, upgrades pip, and installs the core package in editable mode.

To run the OS-specific target directly:

```bash
make install-linux
make install-windows
```

To do the same setup manually from the wrapper root, create a virtual
environment inside `tc-c-kit` and install the package in editable mode:

```bash
python3 -m venv tc-c-kit/.venv
source tc-c-kit/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e './tc-c-kit'
```

The minimum install uses the core package only. The `dev` extra installs the
dependencies used by tests, schema validation, source extraction helpers, and
chart exports.

If you are already inside `tc-c-kit`, use `../.agents/...` for the skill script
and `data/cases/...` for case paths. From the wrapper root, keep the examples in
this runbook unchanged.

## Optional Extras

Install only the surfaces you need:

```bash
python -m pip install -e './tc-c-kit[agentic]'
python -m pip install -e './tc-c-kit[llm]'
python -m pip install -e './tc-c-kit[mcp]'
python -m pip install -e './tc-c-kit[web-local]'
python -m pip install -e './tc-c-kit[documents]'
python -m pip install -e './tc-c-kit[retrieval]'
python -m pip install -e './tc-c-kit[memory-local]'
```

Use `agentic` for the LangGraph runner, `llm` for optional LLM packet helpers,
`mcp` for MCP frontends, `web-local` for local source discovery helpers,
`documents` for parsing and OCR, `retrieval` for local Qdrant/LlamaIndex
search, and `memory-local` for workflow memory.

## Verify the Install

Run the synthetic fixture through the core validator:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate tc-c-kit/data/examples/synthetic_case
```

Check that the case-builder app can plan a dry run:

```bash
PYTHONPATH=tc-c-kit/src python -m case_builder.cli plan tc-c-kit/data/cases/install_smoke \
  --title "Install Smoke Test" \
  --subject "Synthetic public-source smoke test for setup verification"
```

If the package entry point is installed, the same app is available as:

```bash
trcr-case-builder plan tc-c-kit/data/cases/install_smoke \
  --title "Install Smoke Test" \
  --subject "Synthetic public-source smoke test for setup verification"
```

The dry-run planner records intended operations in JSON output. Add `--execute`
only when you want the app to create or modify the case workspace.

## Create the First Case

Initialize a local case workspace:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py init-case tc-c-kit/data/cases/<case_slug> \
  --title "<Case Title>"
```

Register a source manually when it should be tracked before extraction:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py add-source tc-c-kit/data/cases/<case_slug> \
  --title "<Source Title>" \
  --url "<URL or local path>" \
  --source-type news_article \
  --reliability-grade B \
  --notes "Initial source registration"
```

Or capture a public URL directly:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py ingest-url tc-c-kit/data/cases/<case_slug> \
  "<URL>" \
  --source-type news_article \
  --reliability-grade B
```

Draft an extraction packet for review:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID>
```

After the packet is filled and reviewed, import and validate it:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction tc-c-kit/data/cases/<case_slug> \
  tc-c-kit/data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json

python .agents/skills/truecrime-cult-research/scripts/tcr.py validate tc-c-kit/data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py report tc-c-kit/data/cases/<case_slug>
```

## Run the Case-Builder App

The case-builder app wraps the same ledger operations in a resumable workflow.
The ledger under `records/*.jsonl` remains the source of truth.

Dry run:

```bash
trcr-case-builder plan tc-c-kit/data/cases/<case_slug> \
  --title "<Case Title>" \
  --subject "<case subject, source question, names, dates, and places>"
```

Execute deterministic commands:

```bash
trcr-case-builder plan tc-c-kit/data/cases/<case_slug> \
  --title "<Case Title>" \
  --subject "<case subject, source question, names, dates, and places>" \
  --execute
```

Run with LangGraph checkpoints:

```bash
trcr-case-builder plan tc-c-kit/data/cases/<case_slug> \
  --title "<Case Title>" \
  --subject "<case subject, source question, names, dates, and places>" \
  --runner langgraph \
  --checkpoint \
  --execute
```

Resume after human packet review:

```bash
trcr-case-builder resume tc-c-kit/data/cases/<case_slug> \
  --thread <thread_id> \
  --approve-packet <SOURCE_ID>_extraction.json \
  --execute
```

Resume after public-export review:

```bash
trcr-case-builder resume tc-c-kit/data/cases/<case_slug> \
  --thread <thread_id> \
  --approve-export \
  --execute
```

## Optional LLM and Tracing Settings

LLM nodes are disabled unless `--llm` is passed. Configure the model with:

```bash
export TRCR_MODEL=ollama:llama3.1
```

When using a non-local model provider, treat source text egress as a reviewable
event and make sure it is appropriate for the case. LLM output is never
evidence; it must still pass source support, packet review, validation, and
privacy review.

LangSmith tracing is optional:

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=<redacted>
export LANGSMITH_PROJECT=trcr-case-builder-dev
```

Do not send private source text, private-person details, or unredacted case
material to hosted traces.

## Optional Local Services

SearXNG source discovery:

```bash
trcr-case-builder discover-sources tc-c-kit/data/cases/<case_slug> \
  --query "<public source search query>" \
  --searxng-url http://localhost:8080
```

Docling parse and OCR:

```bash
trcr-case-builder parse-source tc-c-kit/data/cases/<case_slug> <SOURCE_ID>
trcr-case-builder ocr-source tc-c-kit/data/cases/<case_slug> <SOURCE_ID>
```

Qdrant-backed local retrieval:

```bash
trcr-case-builder index-case tc-c-kit/data/cases/<case_slug> \
  --qdrant-url http://localhost:6333

trcr-case-builder query-case tc-c-kit/data/cases/<case_slug> \
  "Which claims lack source spans?"
```

Workflow memory:

```bash
trcr-case-builder remember-research-actions tc-c-kit/data/cases/<case_slug> --provider local
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
| `ModuleNotFoundError: case_builder` | Activate `tc-c-kit/.venv`, install `-e './tc-c-kit[dev]'`, or run with `PYTHONPATH=tc-c-kit/src`. |
| `.agents/.../tcr.py` not found | Run from the wrapper root, or use `../.agents/...` from inside `tc-c-kit`. |
| Case files appear in the wrong directory | From the wrapper root, use `tc-c-kit/data/cases/<case_slug>`. From inside `tc-c-kit`, use `data/cases/<case_slug>`. |
| LangGraph imports fail | Install `python -m pip install -e './tc-c-kit[agentic]'`. |
| LLM node imports fail | Install `python -m pip install -e './tc-c-kit[llm]'` and set `TRCR_MODEL`. |
| Parse, OCR, retrieval, or memory commands fail | Install the matching optional extra and start any required local services. |
| A claim is blocked from public export | Keep it internal until source support, contradiction review, source-independence review, and privacy review are complete. |
