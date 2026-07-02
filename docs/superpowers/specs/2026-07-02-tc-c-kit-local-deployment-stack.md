# tc-c-kit Local Deployment Stack

Status: draft design, 2026-07-02
Scope: `tc-c-kit/` deployment assets, packaging, runtime config, and docs

## Goal

Create a self-hosted container deployment for the full CRK kit. The deployment
must run the app, source discovery, vector retrieval, local LLM, local memory,
and document OCR without managed SaaS or hosted runtime services.

The previous packaging treated most of these capabilities as optional. For the
container deployment they are mandatory:

- SearXNG for lead-only source discovery.
- Valkey for SearXNG state/limiter support.
- Qdrant for evidence retrieval and Mem0 vector storage.
- Ollama for all LLM calls.
- Tesseract and Ghostscript in the CRK app image for OCRmyPDF.
- Python runtime extras for agentic, LLM, MCP, web-local, documents,
  retrieval, and memory-local surfaces.

LangSmith and managed SaaS model-provider configuration are out of scope and
should be removed from deployment docs and runtime guidance. Codex and Claude
Code remain valid operator frontends: they may drive the self-hosted stack
through the CLI or MCP server, but they are not CRK app runtime model providers
unless they expose a self-hosted, non-managed local model API in the future. The
default CRK runtime model provider remains local Ollama. The deployment may
download container images, Python packages, and model files during install or
bootstrap, but the running stack must not depend on managed observability,
managed vector stores, or managed model APIs.

## Non-Goals

- No Kubernetes manifests in this phase.
- No managed LangSmith tracing.
- No managed SaaS model providers in runtime config.
- No blocking Codex or Claude Code as user-facing agent hosts; they are allowed
  to operate the local CLI/MCP surface.
- No public exposure by default.
- No automatic crawling beyond explicit SearXNG discovery commands.
- No canonical-record writes outside the existing CRK import and validation
  flow.

## External References

- SearXNG recommends Compose instancing and shows a core service plus
  `searxng-valkey`; its container docs list `/etc/searxng` and
  `/var/cache/searxng` as persistent mount points:
  https://docs.searxng.org/admin/installation-docker.html
- Qdrant's local quickstart uses `qdrant/qdrant`, exposes REST on `6333` and
  gRPC on `6334`, and persists `/qdrant/storage`:
  https://qdrant.tech/documentation/quickstart/
- Ollama's Docker image exposes `11434`, persists `/root/.ollama`, supports CPU
  and GPU variants, and pulls/runs local models inside the container:
  https://hub.docker.com/r/ollama/ollama
- OCRmyPDF requires external OCR/PDF tools from the OS package manager;
  Tesseract and Ghostscript are the relevant system dependencies for this image:
  https://ocrmypdf.readthedocs.io/en/latest/installation.html

## Decisions

| Question | Decision |
| --- | --- |
| Runtime service shape | One Compose stack starts every local service by default: `crk`, `searxng`, `searxng-valkey`, `qdrant`, and `ollama`. |
| App image | A single full-featured app image installs all runtime extras and OCR system packages. |
| Dev dependencies | `dev` remains a test/build extra, not part of the production runtime image. |
| Self-hosted model providers | `ollama:<model>` is supported now. Future providers must expose self-hosted local APIs, such as an OpenAI-compatible local server; managed APIs are not allowed in this deployment. |
| Agent hosts | Codex and Claude Code are supported as user-facing operators over CLI/MCP; they are not CRK runtime model providers unless backed by a self-hosted local API. |
| Observability | Local logs and JSONL research actions only. Remove LangSmith docs/config from this deployment surface. |
| Public ports | Bind service ports to `127.0.0.1` by default. |
| Persistence | Bind mount cases for host visibility; named volumes for Qdrant, Ollama models, SearXNG config/cache, and model caches. |
| GPU support | CPU-only Compose is the baseline. GPU support can be an override file after the base stack works. |
| SearXNG dependency | Include Valkey because SearXNG's container docs and limiter/bot-protection configuration expect it. |

## Runtime Architecture

```text
              host: docker compose
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  docker compose run crk ...                            │
│  docker compose exec crk cr-kit ...         │
│                                                         │
│  ┌────────────┐        ┌──────────────┐                 │
│  │ crk app   │───────▶│ searxng:8080 │────▶ public web │
│  │ full image │        └──────┬───────┘                 │
│  │            │               ▼                         │
│  │            │        ┌──────────────┐                 │
│  │            │        │ valkey:6379  │                 │
│  │            │        └──────────────┘                 │
│  │            │                                         │
│  │            │        ┌──────────────┐                 │
│  │            ├───────▶│ qdrant:6333  │                 │
│  │            │        └──────────────┘                 │
│  │            │                                         │
│  │            │        ┌──────────────┐                 │
│  │            └───────▶│ ollama:11434 │                 │
│  └────────────┘        └──────────────┘                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

The `crk` service is primarily a durable toolbox container for CLI and MCP
workflows. It should keep running so operators can use `docker compose exec`.
One-off commands should also work through `docker compose run --rm crk ...`.

## Required Files

```text
deployment/
  README.md
  Dockerfile
  docker-compose.yml
  .env.example
  searxng/
    settings.yml
    limiter.toml
  scripts/
    bootstrap-ollama.sh
    wait-for-local-stack.sh
    smoke-test.sh
.dockerignore
Makefile
docs/runbook/install.md
docs/runbook/case-workflow.md
docs/case-builder-langgraph.md
README.md
src/case_builder/llm/provider.py
```

## App Image Requirements

The app image must:

- Use Python 3.11 or newer.
- Install system packages for OCR and PDF handling:
  `tesseract-ocr`, `tesseract-ocr-eng`, `ghostscript`, `qpdf`, `pngquant`,
  `unpaper`, `fonts-noto`, and build tools needed for Python wheels.
- Install the package with all runtime extras:
  `.[agentic,llm,mcp,web-local,documents,retrieval,memory-local]`.
- Set local defaults:
  - `CRK_CASES_ROOT=/app/data/cases`
  - `CRK_MODEL=ollama:llama3.1`
  - `CRK_SEARXNG_URL=http://searxng:8080`
  - `CRK_QDRANT_URL=http://qdrant:6333`
  - `OLLAMA_HOST=http://ollama:11434`
  - `HF_HOME=/app/.cache/huggingface`
  - `TRANSFORMERS_CACHE=/app/.cache/huggingface`
- Avoid any `LANGSMITH_*` or SaaS model-provider defaults.
- Run as a non-root user after package installation.
- Include a health/smoke command that validates the bundled synthetic case.

## Compose Requirements

`deployment/docker-compose.yml` must define:

| Service | Image/build | Purpose | Persistence |
| --- | --- | --- | --- |
| `crk` | local build from `deployment/Dockerfile` | CLI/MCP toolbox and case-builder runtime | bind `../data/cases`, `../data/exports`; cache volumes |
| `searxng` | official SearXNG image | lead-only search API at `/search?format=json` | `searxng-config`, `searxng-cache` |
| `searxng-valkey` | Valkey image | SearXNG limiter/cache backing service | named volume if needed |
| `qdrant` | `qdrant/qdrant` | vector store for retrieval and Mem0 | `qdrant-storage` |
| `ollama` | `ollama/ollama` | local model runtime | `ollama-models` |

Default host bindings:

- SearXNG: `127.0.0.1:8080:8080`
- Qdrant REST/UI: `127.0.0.1:6333:6333`
- Qdrant gRPC: `127.0.0.1:6334:6334`
- Ollama: `127.0.0.1:11434:11434`

All services must be on an internal Compose network. Public exposure requires a
deliberate future override.

## Runtime Config Contract

The deployment should introduce environment variables consumed consistently by
CLI, MCP, graph nodes, and docs:

| Variable | Default | Purpose |
| --- | --- | --- |
| `CRK_CASES_ROOT` | `/app/data/cases` | Canonical case workspace root inside the container. |
| `CRK_MODEL` | `ollama:llama3.1` | Local model spec. Only `ollama` is accepted. |
| `CRK_SEARXNG_URL` | `http://searxng:8080` | Default discovery endpoint. |
| `CRK_QDRANT_URL` | `http://qdrant:6333` | Default retrieval endpoint. |
| `CRK_QDRANT_HOST` | `qdrant` | Default Mem0 Qdrant host. |
| `CRK_QDRANT_PORT` | `6333` | Default Mem0 Qdrant port. |
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama HTTP endpoint for LangChain/Ollama clients. |
| `CRK_EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | Local embedding model name. |

Any current code path with hard-coded `localhost` defaults should remain usable
outside containers, but container docs and wrappers should pass the service
hostnames above.

## Self-Hosted Policy

The deployment design must enforce this policy:

- Remove LangSmith from deployment docs and generated env examples.
- Remove managed SaaS model-provider guidance from runtime config.
- Keep Codex and Claude Code guidance only as operator frontend guidance for
  driving local CLI/MCP workflows.
- Make `case_builder.llm.provider` reject managed providers. In this phase it
  should accept only `ollama`; future provider additions must be self-hosted
  local API adapters rather than managed cloud APIs.
- Do not add Codex/Claude Code subprocess adapters to the runtime model-provider
  layer. If an agent-host bridge is needed later, design it separately from LLM
  completion providers and keep it behind explicit user action.
- Remove egress-tagging language that implies supported managed LLM calls.
- Treat SearXNG internet access as explicit public-source discovery, not a
  hosted app dependency.
- Keep all vector storage and workflow memory on the local Qdrant service.
- Keep all LLM calls on the local Ollama service.

## Bootstrap and Operations

Required Make targets:

- `make docker-build`
- `make docker-up`
- `make docker-down`
- `make docker-logs`
- `make docker-smoke`
- `make docker-pull-model`
- `make docker-shell`

Required bootstrap behavior:

1. Build the full app image.
2. Start all services.
3. Wait for Qdrant, SearXNG, and Ollama health endpoints.
4. Pull the default Ollama model.
5. Validate the synthetic case inside the app container.
6. Run a dry case-builder plan inside the app container.

## Validation

The deployment is done when these checks pass:

```bash
docker compose -f deployment/docker-compose.yml config
make docker-build
make docker-up
make docker-pull-model
make docker-smoke
make docker-down
make check
```

The smoke test should verify:

- `cr-kit` imports and runs.
- `crk-mcp` imports or prints help without importing hosted services.
- OCR system binaries exist: `tesseract`, `gs`, `ocrmypdf`.
- Qdrant responds on the Compose hostname.
- SearXNG returns JSON from a benign local discovery query.
- Ollama responds and has the configured model available after bootstrap.
- Synthetic-case validation passes.

## Risks

- Image size will increase substantially because OCR, Docling, retrieval, and
  model dependencies are heavy.
- Sentence-transformers and Ollama model pulls require initial network access;
  repeat runs should rely on persistent caches and named volumes.
- Ollama CPU inference may be slow on non-GPU hosts.
- SearXNG depends on upstream search engines and may encounter rate limiting.
- Qdrant has no auth in the default local quickstart; the Compose file must
  bind only to localhost unless a future secured deployment is designed.
