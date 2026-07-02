# Core Install

## Prerequisites

- Python 3.10 or newer.
- `proto` for the preferred cross-platform task workflow. `moon`, Python,
  `uv`, and Bun are pinned in `.prototools` and installed through proto.
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

Then install the pinned proto toolchain and run the Moon install task from the
repository root:

```bash
proto install
moon run crk:install-dev
```

`moon run crk:install-dev` warms the dev command environment with
`uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' ...`.
New worktrees do not need to copy an existing virtualenv; Moon invokes `uv`
and `uv` prepares the selected editable package environment as needed.

For a minimum runtime install without dev dependencies:

```bash
moon run crk:install
```

Moon is the canonical task runner for installs and local operations. The old
wrapper command surface has been retired so CI, docs, and local shells all use
the same `moon run crk:<task>` form.

Manual fallback without moon:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -c "import pytest; import cli"
```

The minimum install uses the core package only. The `dev` extra installs the
dependencies used by tests, schema validation, source extraction helpers, and
chart exports. Use `crk-ledger` for ledger commands and `data/cases/...` for
case paths.

## Optional Extras

Run commands with only the extra surface they need:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[agentic]' -- cr-kit --help
uv run --cache-dir .uv-cache --no-project --with-editable '.[llm]' -- cr-kit --help
uv run --cache-dir .uv-cache --no-project --with-editable '.[mcp]' -- crk-mcp --help
uv run --cache-dir .uv-cache --no-project --with-editable '.[web-local]' -- cr-kit --help
uv run --cache-dir .uv-cache --no-project --with-editable '.[documents]' -- cr-kit --help
uv run --cache-dir .uv-cache --no-project --with-editable '.[retrieval]' -- cr-kit --help
uv run --cache-dir .uv-cache --no-project --with-editable '.[memory-local]' -- cr-kit --help
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
moon run crk:docker-build
moon run crk:docker-up
moon run crk:docker-pull-model
moon run crk:docker-smoke
```

Codex and Claude Code can operate the self-hosted stack through CLI or MCP.
They are agent hosts, not CRK runtime model providers. No LangSmith, managed
vector store, or managed model-provider configuration is part of this
deployment. See `deployment/README.md`.
