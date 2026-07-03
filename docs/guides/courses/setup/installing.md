# Installing CRK

This guide gets a workstation ready to run CRK commands. It is case-neutral;
the [MKUltra sample course](../samples/mkultra/) is the worked example used by the
other course guides.

## Prerequisites

Install:

- Git.
- Python 3.10 or newer.
- Poppler for PDF text extraction.
- Tesseract and Ghostscript for OCR workflows.
- A shell with standard Unix tools. Windows users should use WSL2 Ubuntu LTS.

On WSL2 Ubuntu:

```bash
sudo apt update
sudo apt install -y git curl python3 poppler-utils tesseract-ocr ghostscript
```

On macOS, install equivalent packages with Homebrew or your package manager.

## Clone The Repository

```bash
git clone git@github.com:StonedAcademia/crime-research-kit.git
cd crime-research-kit
```

If you are working from a monorepo checkout, enter the kit directory before
running commands.

## Install The Toolchain

CRK uses proto and Moon for repeatable local tasks:

```bash
curl -fsSL https://moonrepo.dev/install/proto.sh | bash
exec "$SHELL"
proto install
moon run crk:install-dev
```

The install task uses `uv` and the repo-local `.uv-cache/`. You do not need to
activate a virtualenv for normal course commands.

## Verify The Install

Run the core check:

```bash
moon run crk:check
```

Confirm the entry points:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- cr-kit --help
uv run --cache-dir .uv-cache --no-project --with-editable . -- crk-ledger --help
uv run --cache-dir .uv-cache --no-project --with-editable '.[mcp]' -- crk-mcp --help
```

## Fallback Without Moon

If Moon is not available yet, use `uv` directly:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,mcp,documents,retrieval]' \
  -- python -c "import cli"
```

## Done When

- `moon run crk:check` passes.
- `cr-kit --help` and `crk-ledger --help` render.
- Optional MCP users can render `crk-mcp --help`.
