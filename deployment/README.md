# CRK Self-Hosted Deployment

This deployment runs the full CRK local stack with no managed SaaS runtime
services. Codex and Claude Code may operate the stack through CLI or MCP, but
the CRK app runtime model provider is self-hosted. The default provider is
Ollama.

## Services

| Service | Purpose | Host binding |
| --- | --- | --- |
| `crk` | CLI, LangGraph, MCP, OCR, retrieval, memory, and case-builder toolbox | no public port |
| `searxng` | Lead-only public-source discovery | `127.0.0.1:${CRK_SEARXNG_HOST_PORT:-8080}` |
| `searxng-valkey` | SearXNG limiter/cache backing service | internal only |
| `qdrant` | Evidence and Mem0 vector storage | `127.0.0.1:6333`, `127.0.0.1:6334` |
| `ollama` | Self-hosted LLM runtime | `127.0.0.1:11434` |

All public-facing claims still require source records, validation, review gates,
source-independence review, and privacy review. SearXNG results are leads only.

## First Run

From the repo root:

```bash
cp deployment/.env.example deployment/.env
moon run crk:docker-build
moon run crk:docker-up
moon run crk:docker-pull-model
moon run crk:docker-smoke
```

The first image build and model pull require network access. After that, model
files, Qdrant data, and Hugging Face embedding cache persist in Docker volumes.

## Daily Use

Open a shell in the app container:

```bash
moon run crk:docker-shell
```

Run case-builder commands:

```bash
moon run crk:docker-shell
```

Inside the container shell:

```bash
cr-kit plan /app/data/cases/example_case \
  --title "Example Case" \
  --subject "public-source case question"
```

Run the MCP server from a host agent configuration by pointing the host at
`crk-mcp` inside the app image, or by using the local `uv run` MCP command for
stdio hosts such as Codex and Claude Code.

## Environment

Important defaults:

```text
CRK_MODEL=ollama:llama3.1
CRK_CASES_ROOT=/app/data/cases
CRK_SEARXNG_URL=http://searxng:8080
CRK_SEARXNG_HOST_PORT=18080
SEARXNG_BASE_URL=http://127.0.0.1:18080/
CRK_QDRANT_URL=http://qdrant:6333
CRK_QDRANT_HOST=qdrant
CRK_QDRANT_PORT=6333
OLLAMA_HOST=http://ollama:11434
CRK_EMBED_MODEL=BAAI/bge-small-en-v1.5
```

No managed tracing, hosted vector store, or managed model-provider
configuration is part of this deployment. Future model-provider additions must
expose self-hosted local APIs.

SearXNG is bound to localhost by default. `deployment/.env.example` uses host
port `18080` to avoid common local dev collisions; override
`CRK_SEARXNG_HOST_PORT` and `SEARXNG_BASE_URL` together if needed. If you expose
SearXNG beyond localhost, change `server.secret_key` and revisit the local
limiter setting in `deployment/searxng/settings.yml` first.

## Volumes

| Volume or mount | Purpose |
| --- | --- |
| `data/cases:/app/data/cases` | Host-visible case workspaces. |
| `data/exports:/app/data/exports` | Host-visible cross-case exports. |
| `crk-hf-cache` | Hugging Face embedding model cache. |
| `qdrant-storage` | Qdrant collections and indexes. |
| `ollama-models` | Ollama model files. |
| `searxng-cache` | SearXNG cache and favicon data. |
| `searxng-valkey-data` | Valkey persistence for SearXNG. |

## Operations

```bash
moon run crk:docker-config
moon run crk:docker-up
moon run crk:docker-logs
moon run crk:docker-smoke
moon run crk:docker-down
```

`moon run crk:docker-down` stops containers without deleting volumes.
