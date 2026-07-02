# tc-c-kit Local Deployment Stack Implementation Plan

> **For agentic workers:** Implement this plan task-by-task. Keep deployment
> work in a separate commit series from unrelated skill or MCP changes. Do not
> stage unrelated dirty files.

**Goal:** Build a self-hosted Docker/Compose deployment where every formerly
optional runtime capability is mandatory: SearXNG + Valkey, Qdrant, Ollama,
OCR tooling, LangGraph, MCP, retrieval, Mem0, and document parsing. Remove
LangSmith and managed SaaS model-provider guidance from the deployment path
while keeping Codex and Claude Code as supported user-facing operators over
CLI/MCP.

**Architecture:** A full-featured `trcr` toolbox image runs the CLI, graph, and
MCP surfaces. Compose starts the complete local service set by default. Operators
use Make targets to build, start, bootstrap models, run smoke tests, and shell
into the app container.

**Tech Stack:** Docker Compose, Python 3.11+, Debian slim app image, SearXNG,
Valkey, Qdrant, Ollama, OCRmyPDF, Tesseract, Ghostscript, Make, pytest.

## Global Constraints

- Repo root: `<project_root>/`.
- Preserve the existing TRCR safety model: canonical records are still written
  only through reviewed extraction import paths.
- Treat all runtime extras as mandatory in the deployment image:
  `agentic`, `llm`, `mcp`, `web-local`, `documents`, `retrieval`,
  `memory-local`.
- Do not include LangSmith, managed vector stores, or managed model APIs in
  deployment defaults or docs.
- Codex and Claude Code may be documented as agent hosts that operate the local
  CLI/MCP surface. They are not TRCR runtime model providers unless backed by a
  self-hosted local model API.
- Bind service ports to `127.0.0.1` only.
- Do not rely on Compose profiles for required capabilities; all local services
  start in the base Compose file.
- Avoid introducing new top-level app dependencies unless required by the
  deployment implementation.
- Run `make check` before completing the phase.

## File Structure

End state:

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
docs/mcp-server.md
README.md
src/case_builder/cli.py
src/case_builder/llm/provider.py
src/case_builder/retrieval/index.py
src/case_builder/memory/mem0_provider.py
src/case_builder/ops/sources.py
src/case_builder/ops/query.py
```

---

## Task 1: Make Runtime Defaults Container-Aware and Self-Hosted

**Files:**
- Modify: `src/case_builder/llm/provider.py`
- Modify: `src/case_builder/cli.py`
- Modify: `src/case_builder/ops/sources.py`
- Modify: `src/case_builder/ops/query.py`
- Modify: `src/case_builder/retrieval/index.py`
- Modify: `src/case_builder/memory/mem0_provider.py`
- Add/modify tests as needed.

**Requirements:**

- `TRCR_MODEL` must accept only `ollama:<model>` in this phase.
- Default model remains `ollama:llama3.1`.
- Remove runtime messaging that suggests managed SaaS model provider packages.
- Do not add Codex or Claude Code as `TRCR_MODEL` providers. If they need to
  trigger local workflows later, model them as explicit agent-host bridges
  outside the LLM completion-provider layer.
- Discovery default should read `TRCR_SEARXNG_URL` before falling back to
  `http://localhost:8080`.
- Retrieval default should read `TRCR_QDRANT_URL` before falling back to
  `http://localhost:6333`.
- Mem0 defaults should read `TRCR_QDRANT_HOST`, `TRCR_QDRANT_PORT`,
  `TRCR_MEM0_LLM_PROVIDER`, `TRCR_MEM0_LLM_MODEL`, `TRCR_EMBEDDER_PROVIDER`,
  and `TRCR_EMBED_MODEL`, with local defaults only.
- CLI defaults should mirror env-aware operation defaults instead of baking
  only `localhost`.

**Validation:**

```bash
python -m pytest tests/test_llm_provider.py tests/test_local_stack.py -v
python -m compileall src/case_builder
```

Commit:

```bash
git add src/case_builder tests
git commit -m "feat(deploy): enforce local runtime defaults"
```

---

## Task 2: Remove LangSmith and Managed Provider Guidance

**Files:**
- Modify: `docs/case-builder-langgraph.md`
- Modify: `docs/mcp-server.md`
- Modify: `docs/runbook/install.md`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-07-01-tc-c-kit-agent-system-design.md`
- Modify: any plan docs only when they are active guidance, not historical
  completed context.

**Requirements:**

- Remove LangSmith setup snippets and observability rows.
- Replace provider-pluggable managed model wording with self-hosted runtime
  wording. `ollama` is the initial supported provider; future providers must be
  local/self-hosted APIs.
- Keep Codex and Claude Code references when they describe user-facing CLI/MCP
  operation rather than TRCR runtime model configuration.
- Explicitly state that Codex/Claude Code are agent hosts, not app runtime model
  providers, unless a self-hosted local API exists for them.
- Keep warnings that LLM output is never evidence.
- Keep local logs, research-actions JSONL, reports, and audit outputs as the
  supported observability surfaces.

**Validation:**

```bash
rg -n "LangSmith|LANGSMITH|langchain-anthropic|hosted provider|managed model|SaaS model" README.md docs src
```

Expected: no live deployment/runtime guidance for those terms. Historical plan
mentions may remain only if clearly archived and not part of operator docs.
Codex and Claude Code references are allowed when they describe operating the
local stack through CLI/MCP.

Commit:

```bash
git add README.md docs src
git commit -m "docs(deploy): remove hosted runtime guidance"
```

---

## Task 3: Add the Full App Dockerfile

**Files:**
- Create: `.dockerignore`
- Create: `deployment/Dockerfile`

**Requirements:**

- Base image: Python 3.11 or newer slim Debian image.
- Install OS packages:
  - `tesseract-ocr`
  - `tesseract-ocr-eng`
  - `ghostscript`
  - `qpdf`
  - `pngquant`
  - `unpaper`
  - `fonts-noto`
  - `curl`
  - build tools needed for Python wheels
- Copy only package metadata first for dependency layer caching, then source.
- Install all mandatory runtime extras:
  `pip install -e '.[agentic,llm,mcp,web-local,documents,retrieval,memory-local]'`.
- Create `/app/data/cases`, `/app/data/exports`, and cache directories.
- Use a non-root `trcr` user.
- Default command keeps the toolbox container alive for `docker compose exec`
  or prints help if we choose one-shot mode. Prefer a durable toolbox command
  for Compose.

**Validation:**

```bash
docker build -f deployment/Dockerfile -t tc-c-kit:local .
docker run --rm tc-c-kit:local python -m case_builder.cli --help
docker run --rm tc-c-kit:local tesseract --version
docker run --rm tc-c-kit:local gs --version
docker run --rm tc-c-kit:local ocrmypdf --version
```

Commit:

```bash
git add .dockerignore deployment/Dockerfile
git commit -m "feat(deploy): add full local app image"
```

---

## Task 4: Add Compose Stack and Local Config

**Files:**
- Create: `deployment/docker-compose.yml`
- Create: `deployment/.env.example`
- Create: `deployment/searxng/settings.yml`
- Create: `deployment/searxng/limiter.toml`

**Requirements:**

- Services: `trcr`, `searxng`, `searxng-valkey`, `qdrant`, `ollama`.
- No profiles for required services.
- Host port bindings use `127.0.0.1`.
- Use a named network.
- Add volumes:
  - bind `../data/cases:/app/data/cases`
  - bind or named volume for `../data/exports:/app/data/exports`
  - `trcr-hf-cache:/app/.cache/huggingface`
  - `qdrant-storage:/qdrant/storage`
  - `ollama-models:/root/.ollama`
  - `searxng-config:/etc/searxng` if config is volume-managed, or bind the
    tracked config read-only
  - `searxng-cache:/var/cache/searxng`
- Set container env:
  - `TRCR_CASES_ROOT=/app/data/cases`
  - `TRCR_MODEL=${TRCR_MODEL:-ollama:llama3.1}`
  - `TRCR_SEARXNG_URL=http://searxng:8080`
  - `TRCR_QDRANT_URL=http://qdrant:6333`
  - `TRCR_QDRANT_HOST=qdrant`
  - `TRCR_QDRANT_PORT=6333`
  - `OLLAMA_HOST=http://ollama:11434`
  - `TRCR_EMBED_MODEL=${TRCR_EMBED_MODEL:-BAAI/bge-small-en-v1.5}`
- SearXNG settings should point Valkey/Redis config at the Compose service
  hostname.
- Add healthchecks where the images have shell/curl support; otherwise handle
  readiness in `wait-for-local-stack.sh`.

**Validation:**

```bash
docker compose -f deployment/docker-compose.yml config
docker compose -f deployment/docker-compose.yml up -d
docker compose -f deployment/docker-compose.yml ps
docker compose -f deployment/docker-compose.yml down
```

Commit:

```bash
git add deployment/docker-compose.yml deployment/.env.example deployment/searxng
git commit -m "feat(deploy): add local compose stack"
```

---

## Task 5: Add Bootstrap, Wait, and Smoke Scripts

**Files:**
- Create: `deployment/scripts/bootstrap-ollama.sh`
- Create: `deployment/scripts/wait-for-local-stack.sh`
- Create: `deployment/scripts/smoke-test.sh`

**Requirements:**

- `bootstrap-ollama.sh`:
  - waits for Ollama
  - pulls the configured model from `TRCR_MODEL`
  - lists local models
  - rejects non-ollama model specs
- `wait-for-local-stack.sh`:
  - waits for Qdrant REST
  - waits for SearXNG search endpoint
  - waits for Ollama API
  - exits with clear diagnostics
- `smoke-test.sh`:
  - validates `data/examples/synthetic_case`
  - runs `trcr-case-builder plan ...` dry
  - verifies `trcr-mcp` import or startup help
  - verifies OCR binaries and `ocrmypdf`
  - verifies Qdrant/SearXNG/Ollama connectivity through Compose hostnames
  - avoids writing canonical case records

**Validation:**

```bash
sh -n deployment/scripts/bootstrap-ollama.sh
sh -n deployment/scripts/wait-for-local-stack.sh
sh -n deployment/scripts/smoke-test.sh
```

Commit:

```bash
git add deployment/scripts
git commit -m "feat(deploy): add local stack bootstrap checks"
```

---

## Task 6: Add Make Targets

**Files:**
- Modify: `Makefile`

**Targets:**

- `docker-build`
- `docker-up`
- `docker-down`
- `docker-logs`
- `docker-shell`
- `docker-pull-model`
- `docker-smoke`
- `docker-clean` if it only stops/removes containers and clearly warns before
  deleting volumes. Do not delete volumes by default.

**Requirements:**

- Default Compose file variable:
  `COMPOSE_FILE ?= deployment/docker-compose.yml`
- All targets use `docker compose -f $(COMPOSE_FILE)`.
- `docker-smoke` depends on the stack being up and runs the app smoke script
  inside the `trcr` service.
- `docker-pull-model` runs the bootstrap script inside the `trcr` service.

**Validation:**

```bash
make -n docker-build
make -n docker-up
make -n docker-pull-model
make -n docker-smoke
make -n docker-down
```

Commit:

```bash
git add Makefile
git commit -m "feat(deploy): add local stack make targets"
```

---

## Task 7: Document the Deployment Runbook

**Files:**
- Create: `deployment/README.md`
- Modify: `docs/runbook/install.md`
- Modify: `README.md`

**Requirements:**

- Document the self-hosted policy.
- Document the mandatory services.
- Document first run:

```bash
cp deployment/.env.example deployment/.env
make docker-build
make docker-up
make docker-pull-model
make docker-smoke
```

- Document daily use:

```bash
make docker-shell
docker compose -f deployment/docker-compose.yml exec trcr trcr-case-builder --help
```

- Document port bindings, volumes, and how to stop the stack.
- Document that no LangSmith or managed SaaS model provider is configured.
- Document that Codex and Claude Code can operate the local stack through CLI
  or MCP without changing TRCR's self-hosted runtime provider boundary.
- Document that SearXNG performs explicit public-source discovery and should
  not be treated as evidence.
- Document that model/package/image downloads are setup-time network activity;
  runtime AI/vector services stay local.

**Validation:**

```bash
rg -n "LangSmith|LANGSMITH|SaaS model|hosted model provider|managed model" deployment README.md docs/runbook/install.md
```

Expected: no deployment runbook references to hosted observability or hosted
LLM runtime providers. Codex and Claude Code references are allowed only as
agent-host/operator guidance.

Commit:

```bash
git add deployment/README.md README.md docs/runbook/install.md
git commit -m "docs(deploy): document local container stack"
```

---

## Task 8: End-to-End Verification

Run:

```bash
docker compose -f deployment/docker-compose.yml config
make docker-build
make docker-up
make docker-pull-model
make docker-smoke
make check
make docker-down
git status --short --branch
```

Expected:

- Compose config renders.
- App image builds.
- All five services start.
- Ollama model is present.
- Smoke script passes.
- `make check` passes.
- Worktree contains only intended deployment/docs/code changes.

Final commit if any validation fixes were needed:

```bash
git add <fixed files>
git commit -m "test(deploy): verify local compose stack"
```
