# TRCR Self-Hosted Deployment

This deployment runs the full TRCR local stack with no managed SaaS runtime
services. Codex and Claude Code may operate the stack through CLI or MCP, but
the TRCR app runtime model provider is self-hosted. The default provider is
Ollama.

## Services

| Service | Purpose | Host binding |
| --- | --- | --- |
| `trcr` | CLI, LangGraph, MCP, OCR, retrieval, memory, and case-builder toolbox | no public port |
| `searxng` | Lead-only public-source discovery | `127.0.0.1:8080` |
| `searxng-valkey` | SearXNG limiter/cache backing service | internal only |
| `qdrant` | Evidence and Mem0 vector storage | `127.0.0.1:6333`, `127.0.0.1:6334` |
| `ollama` | Self-hosted LLM runtime | `127.0.0.1:11434` |

All public-facing claims still require source records, validation, review gates,
source-independence review, and privacy review. SearXNG results are leads only.

## First Run

From the repo root:

```bash
cp deployment/.env.example deployment/.env
moon run trcr:docker-build
moon run trcr:docker-up
moon run trcr:docker-pull-model
moon run trcr:docker-smoke
```

The first image build and model pull require network access. After that, model
files, Qdrant data, and Hugging Face embedding cache persist in Docker volumes.

## Daily Use

Open a shell in the app container:

```bash
moon run trcr:docker-shell
```

Run case-builder commands:

```bash
moon run trcr:docker-shell
```

Inside the container shell:

```bash
trcr-case-builder plan /app/data/cases/example_case \
  --title "Example Case" \
  --subject "public-source case question"
```

Run the MCP server from a host agent configuration by pointing the host at
`trcr-mcp` inside the app image, or by using the local virtualenv install for
stdio hosts such as Codex and Claude Code.

## Environment

Important defaults:

```text
TRCR_MODEL=ollama:llama3.1
TRCR_CASES_ROOT=/app/data/cases
TRCR_SEARXNG_URL=http://searxng:8080
TRCR_QDRANT_URL=http://qdrant:6333
TRCR_QDRANT_HOST=qdrant
TRCR_QDRANT_PORT=6333
OLLAMA_HOST=http://ollama:11434
TRCR_EMBED_MODEL=BAAI/bge-small-en-v1.5
```

No LangSmith, hosted vector store, or managed model-provider configuration is
part of this deployment. Future model-provider additions must expose
self-hosted local APIs.

SearXNG is bound to localhost by default. If you expose it beyond localhost,
change `server.secret_key` in `deployment/searxng/settings.yml` first.

## Volumes

| Volume or mount | Purpose |
| --- | --- |
| `data/cases:/app/data/cases` | Host-visible case workspaces. |
| `data/exports:/app/data/exports` | Host-visible cross-case exports. |
| `trcr-hf-cache` | Hugging Face embedding model cache. |
| `qdrant-storage` | Qdrant collections and indexes. |
| `ollama-models` | Ollama model files. |
| `searxng-cache` | SearXNG cache and favicon data. |
| `searxng-valkey-data` | Valkey persistence for SearXNG. |

## Operations

```bash
moon run trcr:docker-config
moon run trcr:docker-up
moon run trcr:docker-logs
moon run trcr:docker-smoke
moon run trcr:docker-down
```

`moon run trcr:docker-down` stops containers without deleting volumes. The
Makefile still provides compatibility wrappers such as `make docker-up`.
