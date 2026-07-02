# Lesson 1: Greenfield Install

This lesson assumes a new Windows 11 workstation with WSL2 Ubuntu LTS. Linux
and macOS users can skip the Windows-only step and start at system packages.

## Windows 11 And WSL2

Open PowerShell as the user who will run CRK:

```powershell
wsl --install -d Ubuntu-24.04
wsl --set-default-version 2
wsl -d Ubuntu-24.04
```

Inside Ubuntu, update packages and install the source-handling tools used in
this course:

```bash
sudo apt update
sudo apt install -y git curl python3 poppler-utils tesseract-ocr ghostscript
```

Linux users can run the same package command with their distribution's package
manager. macOS users should install Git, Python 3.10 or newer, Poppler,
Tesseract, and Ghostscript through Homebrew or their preferred package manager.

## Clone And Install CRK

Clone the repository and enter the kit directory:

```bash
git clone git@github.com:StonedAcademia/true-crime-research-agent.git
cd true-crime-research-agent/tc-c-kit
```

Install proto, the pinned toolchain, and warm the development command
environment:

```bash
curl -fsSL https://moonrepo.dev/install/proto.sh | bash
exec "$SHELL"
proto install
moon run crk:install-dev
```

The install task uses `uv` with the repo-local `.uv-cache/`; it does not require
copying or activating a worktree-local virtualenv. If Moon is unavailable after
bootstrap, use the direct `uv` fallback:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,mcp,documents,retrieval]' \
  -- python -c "import cli"
```

## Verify The Workstation

Run the fixture validator from the repository root:

```bash
moon run crk:check
```

Then confirm the installed entry points:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- cr-kit --help
uv run --cache-dir .uv-cache --no-project --with-editable '.[mcp]' -- crk-mcp --help
```

The `moon run crk:check` fixture validation is the safest first smoke test
because it uses the core stdlib skill path. The packaged entry points are used
for the case-builder app and MCP workflows through `uv run`.

## Create The Course Case

Initialize the local ignored case workspace:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  python .agents/skills/truecrime-cult-research/scripts/tcr.py init-case \
  data/cases/mkultra_course \
  --title "MKUltra Source-Traceable Course Case"
```

Expected local layout:

```text
data/cases/mkultra_course/
  raw/downloads/
  raw/sources/
  records/
  staging/extractions/
  exports/
```

`data/cases/**` is ignored by git. Keep downloaded PDFs, extracted text,
draft packets, reports, charts, and exports there unless a maintainer
explicitly asks for a fixture.

## Optional Local Services

SearXNG, Qdrant, Ollama, OCRmyPDF, and memory providers are optional. They can
make discovery, retrieval, OCR, and agent memory easier, but they do not change
the evidence rule:

```text
public point -> source ID -> locator -> reliability grade -> status -> review
```

LLM output is never evidence. It can suggest extraction candidates only.
