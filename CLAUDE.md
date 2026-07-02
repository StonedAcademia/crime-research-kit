# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

CRK is a local-first research kit for public-interest true crime / cult-origin research. It turns public sources into a source-traceable JSONL case ledger (sources, claims, entities, events, relationships, …) with validation, privacy review, and public-safe exports. `AGENTS.md` holds the persistent project rules and applies here too.

## Commands

```bash
# Setup (run from repo root; proto/moon use the pinned .prototools versions)
moon run crk:install-dev

# Quick check after modifying scripts or schemas (compileall + ledger validation)
moon run crk:check

# Tests (grouped by directory; conftest.py auto-applies the matching marker)
moon run crk:test                               # full suite
moon run crk:test-unit                          # unit lane
moon run crk:test-governance                    # policy/schema/doc-drift checks
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest tests/runtime/integration/operations/case/test_runner.py::test_name  # single test
```

Test categories: `unit`, `integration`, `e2e` (optional extras may skip), `governance` (repo policy, schema, and generated-doc drift), `smoke`.

The two CLIs:

```bash
# Canonical ledger CLI
uv run --cache-dir .uv-cache --no-project --with-editable . -- crk-ledger <init-case|ingest-url|draft-extraction|import-extraction|validate|report|export-manim|...> data/cases/<case_slug>

# Case-builder agent app (installed entry point, or PYTHONPATH=src python -m cli)
cr-kit <plan|parse-source|ocr-source|index-case|query-case|discover-sources|...> data/cases/<case_slug>
```

Self-hosted container stack (SearXNG, Qdrant, Ollama, MCP, ...): `moon run crk:docker-build`, `moon run crk:docker-up`, `moon run crk:docker-pull-model`, `moon run crk:docker-smoke`. See `deployment/README.md`.

## Versioning and changelog workflow

CRK is still pre-1.0. Use SemVer, but treat minor versions as release bands until the public API and operator contract are intentionally stabilized. Patch bumps are only for compatible fixes after a real tag exists; do not invent patch history for untagged fixes.

For release prep:

```bash
git log --oneline --reverse <last_tag>..HEAD   # or all history if no tags exist
git tag --list 'v<version>'
git ls-remote --tags origin 'v<version>'
```

Update `pyproject.toml` and `CHANGELOG.md` together. Keep `## [Unreleased]`, add a dated `## [MAJOR.MINOR.PATCH] - YYYY-MM-DD` section, and summarize real user/operator-facing changes under Keep a Changelog categories such as `Added`, `Changed`, `Security`, and `Fixed`. Avoid placeholder release notes.

Validate and tag locally:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest tests/quality/governance/platform/test_release_readiness.py -q
git tag -a v<version> -m "CRK v<version>"
moon run crk:release-check
```

Release tags are annotated `vMAJOR.MINOR.PATCH` tags. Do not push release tags unless explicitly asked.

## Architecture

**The JSONL ledger is canonical.** Everything else — retrieval indexes, memory, parse artifacts, exports — is rebuildable. A case lives at `data/cases/<case_slug>/` with append-oriented records in `records/*.jsonl` (one schema per record type in `docs/schemas/`), staged LLM extraction packets in `staging/extractions/`, and generated output in `exports/`. `data/cases/` and `data/exports/` are gitignored working areas; the reusable fixture is `data/examples/synthetic_case/`.

Two implementation layers share that ledger:

1. **Skills and ledger CLI** — `crk-ledger` is a stdlib-only packaged CLI implementing the full ledger contract (init, ingest, extraction staging/import, validate, audits, exports). `docs/guides/skill-api-spec.md` is the machine-facing contract for its operations and payload shapes. Sixteen adjacent skills under `.agents/skills/` (legal-court-records, missing-persons-case, privacy-redaction-audit, …) extend the same case ledger for domain-specific packets.
2. **`src/`** — the agent app. Frontends (CLI in `cli.py`, LangGraph workflow in `pipeline/graph/`, MCP server in `adapters/interfaces/mcp/`) never touch `crk-ledger` or the ledger directly; they go through the typed ops core in `adapters/ops/` (`OpResult`, `CrkRunner`, safety `policy`). `pipeline/graph/` has a LangGraph build plus a sequential fallback and stops at a human review gate. Optional-dependency subsystems: `adapters/io/parsing/` (Docling/OCRmyPDF), `adapters/io/retrieval/` (LlamaIndex/Qdrant), `core/memory/` (Mem0/local), `adapters/io/acquisition/` (SearXNG discovery).

Lane/template vocabulary is canonical in `docs/registry/`; the tables in `.agents/skills/truecrime-cult-research/references/lane_registry.md` and `.agents/skills/public-records-router/references/routing_matrix.md` are generated from it, and governance tests catch drift between them. Update the registry shards first.

## Repo constraints

- Most work should start on `dev` or a focused sub-branch such as `feat/*`, `fix/*`, `docs/*`, `gov/*`, `test/*`, `chore/*`, or `ci/*`. Treat `canary` and `hotfix/*` as stabilization lanes for tidy-up, release polish, gate fixes, small regressions, and last-mile corrections. Keep `main` for primary deployments, release integration, and mainline maintenance unless the user explicitly directs otherwise.
- Keep branch and commit hygiene visible: check `git status --short --branch` before work and before staging, branch before substantial edits, stage only intended paths, and commit frequently in cohesive reviewable slices after relevant checks pass. Do not include unrelated dirty files or revert work you did not create.
- Every Python module in `src/` stays under 200 non-comment LOC, and every Python-bearing directory keeps a `README.md` — both enforced by `tests/quality/governance/test_repository_shape.py`.
- Repository shape is governed by `tests/quality/governance/test_repository_shape.py`: each governed directory has 1-4 direct files and 0-3 direct child directories, and governed files stay under 200 non-comment LOC. Only `data/` and `docs/superpowers/` are skipped.
- Name files and directories by intent. Use domain/workflow names such as `schemas/evidence`, `runbooks/setup`, or `scripts/checks`; do not create vague catch-all folders to pass the counts. Check the governance output for every target directory before and after restructuring.
- The package has a small pinned required-dependency set (`jsonschema`, `pydantic`, `pydantic-settings`, `httpx`, `typer`, `jinja2`) enforced by `tests/quality/governance/platform/test_packaging_policy.py`; do not add required dependencies without updating that allowlist deliberately. Heavier features stay behind the optional extras in `pyproject.toml` (`dev`, `agentic`, `mcp`, `documents`, `retrieval`, `memory-local`, `web-local`) and must degrade gracefully (import lazily, skip tests) when absent. Pydantic contract: `BaseModel` for records/packets/manifests/serialized artifacts; `BaseSettings` only at process boundaries (CLI/MCP startup), constructed once with values passed inward.

## Research-content rules

When writing or generating case data, code paths, prompts, or docs, preserve the safety contract (full version in `AGENTS.md` and `docs/guides/skill-api-spec.md`):

- Every claim traces `claim → source_ids → reliability_grade → confidence/status → privacy_review` before public export; AI-generated summaries are never evidence.
- Never infer guilt, membership, motive, or participation from proximity/co-mention; automation-created co-mention records must be `status: unverified`, low confidence, `public_export: false`.
- Only apply labels like suspect/perpetrator/cult member if a cited source uses that wording; prefer neutral roles (`person_mentioned`, `witness`, `former_member`, …).
- Exports are public-safe by default; `--include-private` is an explicit opt-in for internal review. Private-person details (addresses, contacts, minors, medical) stay redacted by default.
- Preserve uncertainty in `status`/`confidence`/`notes` instead of smoothing it away; use `assertion_type` and `independence_group` to keep source framing and wire-copy reuse visible.

## Orchestration workflow  
If you are Fable and have Codex as a plugin then listen to the following prompt otherwise skip:

You (Fable) are the orchestrator. Plan, decompose, synthesize.  
Reasoning-heavy phases → deep-reasoner  
Mechanical work → fast-worker  
Codex (/codex:rescue --background) is a cracked engineer on par with deep-reasoner, from a different perspective. Treat as a peer, not a reviewer.  
High-stakes decisions: task Opus + Codex on the same problem in parallel, synthesize the best of both, without showing either the other's answer. Keep your own context lean.
