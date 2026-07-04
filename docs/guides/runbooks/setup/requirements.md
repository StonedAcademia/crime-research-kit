# Setup Requirements

This guide defines the local requirements for running CRK from a fresh machine.
It covers the lightweight ledger workflow, local development, optional document
processing, retrieval and memory services, MCP, and the self-hosted container
stack.

CRK is local-first. Optional services can make discovery, retrieval, memory, OCR,
and LLM-assisted workflows easier, but they do not change the evidence rule:
public claims still need source records, validation, contradiction review,
source-independence review, privacy review, and public-export review.

## Supported Workloads

| Workload | Use it for | Recommended baseline |
| --- | --- | --- |
| Ledger-only | `crk-ledger`, repo-local skills, JSONL case records, validation, reports, and public-safe exports. | 2 CPU cores, 4 GB RAM, 2 GB free disk. |
| Local development | `moon run crk:check`, `moon run crk:test`, schema validation, source extraction helpers, chart exports, and docs work. | 4 CPU cores, 8 GB RAM, 10 GB free disk. |
| Documents and OCR | PDF parsing, OCRmyPDF, Tesseract, Ghostscript, image conversion, and larger source bundles. | 4+ CPU cores, 16 GB RAM, 20 GB free disk plus source storage. |
| Retrieval and memory | Qdrant, LlamaIndex, embedding cache, local query indexes, and Mem0-backed workflow memory. | 4-8 CPU cores, 16-32 GB RAM, 25-50 GB free disk for indexes and embedding cache. |
| Full self-hosted stack | CRK app container, SearXNG, Valkey, Qdrant, Ollama, OCR tooling, retrieval, memory, LangGraph, and MCP. | 8+ CPU cores, 32 GB RAM, 50-100 GB free disk. |
| Ollama LLM workflows | Local model runtime for optional LLM nodes and packet helpers. | 8+ CPU cores for CPU inference, or a local GPU; reserve model-specific disk and VRAM. |

The numbers above are practical starting points, not hard limits. Large PDF
collections, long OCR jobs, vector indexes, and local LLM models are the parts
that usually drive hardware needs upward.

## Operating System

| Platform | Support level | Notes |
| --- | --- | --- |
| Linux | Preferred. | Best path for Docker, OCR packages, and long-running local services. |
| macOS | Supported. | Works for core development and Docker Desktop. Install OCR packages with Homebrew or use the container stack. |
| Windows | Supported through PowerShell bootstrap and WSL. | WSL2 with Ubuntu is recommended for OCR, Docker, and shell parity with docs examples. |

Commands in setup runbooks assume a POSIX shell from the `tc-c-kit` repository
root unless the example is explicitly marked as PowerShell.

## Required Toolchain

The repository pins its normal toolchain in `.prototools`:

| Tool | Pinned version | Required for |
| --- | --- | --- |
| `proto` | `0.58.0` | Installing the pinned local toolchain. |
| `moon` | `2.3.3` | Canonical task runner for install, checks, tests, Docker operations, and release checks. |
| `python` | `3.11.15` | Default development runtime. The package supports Python `>=3.10`. |
| `uv` | `0.11.2` | Editable package environments and command execution. |
| `bun` | `1.3.11` | Optional Phanestead UFB bundle export support. |

Bootstrap the minimum toolchain from a fresh checkout:

```bash
./deployment/scripts/bootstrap.sh
```

```powershell
.\deployment\scripts\bootstrap.ps1
```

Manual setup should still install the same pinned tools before running Moon
tasks:

```bash
proto install
moon run crk:install-dev
moon run crk:check
```

## Python Package Surfaces

The core package has no required runtime dependencies beyond Python. Optional
extras enable larger surfaces:

| Extra | Enables |
| --- | --- |
| `dev` | Tests, JSON Schema validation, source extraction helpers, pandas/networkx exports, and local development checks. |
| `agentic` | LangGraph workflow runner and SQLite checkpoint support. |
| `llm` | LangChain and Ollama-facing LLM packet helpers. |
| `mcp` | `crk-mcp` stdio server for MCP hosts. |
| `web-local` | Local discovery and web-source helpers. |
| `documents` | Docling, OCRmyPDF, Pillow, and PyMuPDF parsing/OCR support. |
| `retrieval` | Qdrant client, LlamaIndex, embeddings, and local vector search. |
| `memory-local` | Mem0 plus Qdrant-backed workflow memory. |
| `governance` | Release, license, audit, and SBOM tooling. |

Install only the surface you need for a command:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[mcp]' -- crk-mcp --help
uv run --cache-dir .uv-cache --no-project --with-editable '.[documents]' -- cr-kit --help
uv run --cache-dir .uv-cache --no-project --with-editable '.[retrieval]' -- cr-kit --help
```

## System Packages

Core ledger work needs Git, Python, `proto`, `moon`, and `uv`. Optional document
workflows need OCR and PDF utilities from the host OS unless you run them inside
the CRK container image.

| Package | Needed for |
| --- | --- |
| `git` | Cloning and normal repository workflow. |
| `curl` | Bootstrap scripts and simple service checks. |
| `tesseract-ocr` plus English language data | OCR text recognition. |
| `ghostscript` | OCRmyPDF and PDF processing. |
| `qpdf` | PDF normalization used by OCR tooling. |
| `unpaper` | OCR cleanup support. |
| `fonts-noto` | More reliable document and image rendering in container exports. |
| `libgl1`, `libglib2.0-0` | Image/document parsing libraries that need GUI-related shared libraries on Linux. |
| `pngquant` | Image optimization for generated assets. |
| `build-essential` | Native wheels or local builds when Python packages need compilation. |

The self-hosted Docker image installs those packages in
`deployment/Dockerfile`.

## Optional Local Services

| Service | Default binding | Required for |
| --- | --- | --- |
| SearXNG | `127.0.0.1:${CRK_SEARXNG_HOST_PORT:-8080}` | Lead-only public-source discovery. |
| Valkey | Internal Docker network only. | SearXNG limiter/cache backing service. |
| Qdrant | `127.0.0.1:6333`, `127.0.0.1:6334` | Evidence retrieval and Mem0 vector storage. |
| Ollama | `127.0.0.1:11434` | Self-hosted LLM runtime for optional LLM workflows. |

Start the full local stack only when you need those services:

```bash
./deployment/scripts/bootstrap.sh --configure --workflow self-hosted
moon run crk:docker-build
moon run crk:docker-up
moon run crk:docker-pull-model
moon run crk:docker-smoke
```

SearXNG results are leads only. Qdrant, memory, embeddings, and model responses
are operational context only; they are not evidence and do not replace cited
source spans in the ledger.

## Docker Requirements

The self-hosted stack requires Docker Engine or Docker Desktop with Compose v2.
Allocate enough Docker resources before starting the full stack:

| Docker resource | Suggested allocation |
| --- | --- |
| CPUs | 4 minimum; 8+ for Ollama and OCR-heavy use. |
| Memory | 16 GB minimum; 32 GB for comfortable full-stack use. |
| Disk | 50 GB minimum for images, case files, indexes, caches, and one local model; 100 GB is safer for repeated case work. |

The stack persists data in Docker volumes for Ollama models, Qdrant storage,
Hugging Face cache, SearXNG cache, and Valkey data. Host-visible case work lives
under `data/cases/` and cross-case exports under `data/exports/`.

## Storage Planning

Plan disk around the data you intend to keep:

| Data | Location | Notes |
| --- | --- | --- |
| Case workspaces | `data/cases/<case_slug>/` | Ignored by Git except for `.gitkeep`; contains records, staging packets, and exports. |
| Cross-case exports | `data/exports/` | Generated output, ignored by Git. |
| Downloaded PDFs and source captures | Case workspace paths | Size depends on the case corpus; keep originals when they support citation. |
| OCR and parse artifacts | Case workspace paths | Can grow quickly for large PDFs. |
| Qdrant indexes | Docker volume or local service storage | Rebuildable operational index, not evidence. |
| Hugging Face cache | Docker volume or user cache | Embedding model cache. |
| Ollama models | Docker volume or Ollama model directory | Model downloads can be many GB each. |

Keep case workspaces on encrypted storage when they contain sensitive research
notes, non-public drafts, or private-person details that should never be
published.

## Network Requirements

Network access is needed for first install, package downloads, container image
pulls, model downloads, public-source capture, and optional SearXNG discovery.
After the stack is built and models are downloaded, many validation, ledger,
OCR, retrieval, and export workflows can run locally.

Do not expose local services to the public internet by default. The compose
stack binds SearXNG, Qdrant, and Ollama to localhost. If SearXNG is exposed
beyond localhost, generate an ignored local settings file instead of editing the
tracked one:

```bash
python deployment/scripts/bootstrap_env.py configure \
  --workflow exposed-searxng \
  --non-interactive
```

The helper writes ignored local files with restricted permissions and redacts the
generated SearXNG secret in command output.

## Minimum Fresh Install Checklist

Use this checklist for a greenfield machine:

1. Install Git and clone the repository.
2. Install `proto`, `moon`, Python, and `uv` through the bootstrap script.
3. Run `moon run crk:install-dev`.
4. Run `moon run crk:check`.
5. Install OCR system packages only if source parsing or OCR is needed.
6. Install Docker and run the self-hosted stack only if SearXNG, Qdrant,
   Ollama, memory, MCP, or containerized OCR are needed.

Continue with [Initial App Install](install.md) after the requirements are met.
