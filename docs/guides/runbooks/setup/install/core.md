# Core Install

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

## Install The Core Kit

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
chart exports. Use `.agents/...` for the skill script and `data/cases/...` for
case paths.

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
