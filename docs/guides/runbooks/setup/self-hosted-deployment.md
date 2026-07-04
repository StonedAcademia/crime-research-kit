# Self-Hosted Deployment Runbook

This runbook operates the local CRK container stack from the `tc-c-kit`
repository root. The stack runs the CRK app, SearXNG, Valkey, Qdrant, Ollama,
OCR tooling, retrieval, memory, LangGraph, and MCP without managed SaaS runtime
services.

## Safety Boundary

SearXNG results are leads only. Public-facing claims still require source
records, validation, contradiction review, source-independence review, privacy
review, and public-export review before use.

Codex and Claude Code may operate the stack through CLI or MCP. They are agent
hosts, not CRK runtime model providers. The runtime model provider defaults to
self-hosted Ollama.

## Services

| Service | Purpose | Host binding |
| --- | --- | --- |
| `crk` | CLI, LangGraph, MCP, OCR, retrieval, memory, and case-builder toolbox. | No public port. |
| `searxng` | Lead-only public-source discovery. | `127.0.0.1:${CRK_SEARXNG_HOST_PORT:-8080}` |
| `searxng-valkey` | SearXNG limiter/cache backing service. | Internal only. |
| `qdrant` | Evidence and Mem0 vector storage. | `127.0.0.1:6333`, `127.0.0.1:6334` |
| `ollama` | Self-hosted LLM runtime. | `127.0.0.1:11434` |

## First Run

Create the deployment environment file:

```bash
./deployment/scripts/bootstrap.sh --configure --workflow self-hosted
```

For an unattended default profile:

```bash
python deployment/scripts/bootstrap_env.py configure \
  --workflow self-hosted \
  --non-interactive
```

Validate the composed configuration:

```bash
moon run crk:docker-config
```

Build and start the stack:

```bash
moon run crk:docker-build
moon run crk:docker-up
```

Pull the default Ollama model and run the app smoke check:

```bash
moon run crk:docker-pull-model
moon run crk:docker-smoke
```

Moon is the canonical task runner for container operations in local shells and
CI.

The first image build and model pull require network access. Model files,
Qdrant data, Hugging Face embedding cache, and SearXNG cache persist in Docker
volumes after the first run.

## Daily Operation

Start or refresh the stack:

```bash
moon run crk:docker-up
moon run crk:docker-smoke
```

Open a shell in the app container:

```bash
moon run crk:docker-shell
```

Inside the container, case work lives under `/app/data/cases`:

```bash
cr-kit plan /app/data/cases/example_case \
  --title "Example Case" \
  --subject "public-source case question"
```

Follow logs when investigating startup or service failures:

```bash
moon run crk:docker-logs
```

Stop containers without deleting volumes:

```bash
moon run crk:docker-down
```

## Environment Defaults

Important runtime defaults and generated local-stack values:

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

No LangSmith, hosted vector store, or managed model-provider configuration is
part of this deployment. Future model-provider additions must expose
self-hosted local APIs.

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

## Checks

Use these checks before relying on the stack for case work:

```bash
moon run crk:docker-config
moon run crk:docker-up
moon run crk:docker-smoke
```

`deployment/.env.example` uses SearXNG host port `18080` to avoid common local
dev collisions. Override `CRK_SEARXNG_HOST_PORT` and `SEARXNG_BASE_URL`
together when another port is preferred. If SearXNG is exposed beyond
localhost, run the `exposed-searxng` bootstrap workflow so
`deployment/searxng/settings.local.yml` receives a generated `secret_key` and
`CRK_SEARXNG_SETTINGS_FILE` points Compose at that ignored local file.
