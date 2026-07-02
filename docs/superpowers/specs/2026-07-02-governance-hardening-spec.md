# CRK Governance & CI Hardening — Program Spec

Date: 2026-07-02. Status: approved for execution.
Companion plan: `docs/superpowers/plans/2026-07-02-governance-hardening-plan.md`.

## 1. Goal

Turn the requirement list (repo structure, code boundaries, security/local-only,
data safety, docs drift, packaging, CI/release) into enforced, locally runnable
gates. Philosophy, confirmed against the existing suite: **governance is pytest,
stdlib-first, offline-first**. External tools are pinned, wrapped in `make`/moon
targets, and isolated to an explicit audit lane so the dev inner loop never
needs the network.

## 2. Current state (survey findings this spec builds on)

- Governance suite exists: `tests/quality/governance/` (repo shape 1-4 files / 0-3 dirs,
  200 non-comment LOC, schemas, lane-registry drift, skill docs). Extend, never
  duplicate.
- CI is **moonrepo**, not GitHub Actions: `moon.yml` tasks, `.moon` pre-push hook
  running `deployment/scripts/checks/branch_gate.py` (dev → check+smoke;
  canary → +governance; main → full suite). The Makefile delegates to moon.
- `.github/` does not exist yet and **is governed** by the repo-shape test
  (≤4 direct files, ≤3 child dirs, YAML < 200 non-comment LOC). CI layout must
  fit that budget.
- `tcr.py` already ships the data-safety audits: `audit-public-export`,
  `audit-privacy-redactions`, `audit-contradictions`,
  `audit-source-independence`, `review-narrative-readiness`.
- Exactly two network call sites exist: `src/adapters/io/acquisition/search.py`
  and `tcr.py` URL ingestion. Env reads are centralized in
  `src/core/config.py`; ~16 distinct env vars across code + deployment.
- No LICENSE, no CHANGELOG, no lockfile, no secret scanning, no SBOM/license
  tooling, no import-boundary tests, no link checker.
- Working tree is dirty: doc/skill edits plus untracked
  `.agents/skills/criminal-research/` referencing a `criminal-research` template
  that must be registered in `docs/registry/` before the skill is tracked, or
  the skill-docs governance tests fail.

## 3. Enforcement layering (decision)

| Concern | Layer |
|---|---|
| Naming, doc paths, README coverage, import boundaries, lazy imports, network ban, env vars, SaaS denylist, fixture schemas, privacy/provenance, docs drift, runbook coverage, extras grouping, secret-pattern floor, CI/make parity | pytest `-m governance` (stdlib only) |
| gitleaks, pip-audit, pip-licenses, lychee external links | `make audit`-lane targets + CI jobs (pinned external tools; network allowed here only) |
| SBOM, reproducible build, changelog gate | release lane (`make sbom` / tag-triggered CI) |

Rule: if it is decidable from tracked files with stdlib, it is a governance
test. If it needs a binary or a remote DB, it lives in the audit/release lane
with a `make` mirror that degrades gracefully offline.

## 4. Tool pins (external resources — acquired in Phase 1)

| Tool | Version | Delivery | Network? |
|---|---|---|---|
| gitleaks | v8.30.1 | pinned binary, sha256-verified fetch script, cached | fetch only |
| lychee | 0.23.0 | pinned binary, same fetch script | fetch + link checks (non-blocking) |
| pip-audit | 2.10.1 | new `governance` extra | yes (advisory DB) — best-effort offline |
| pip-licenses | 5.5.5 | `governance` extra | no |
| cyclonedx-bom | 7.3.0 | `governance` extra | no |
| build | >=1.2 | `governance` extra | no (with cached wheels) |

Manifest with versions + checksums: `deployment/tooling/manifest.json`.
Fetcher: `deployment/scripts/tools/fetch_governance_tools.py` (stdlib).
Binaries land in a gitignored `deployment/tooling/bin/`.

## 5. Policies

- **Vague-dir denylist**: `misc`, `old`, `temp`, `tmp`, `stuff`, `util`,
  `utils`, `helpers`, `common`, `shared`, `new`, `junk`, `scratch` — blocked as
  directory names repo-wide (tracked files), with an explicit allowlist constant
  (initially empty) for approved exceptions.
- **Generic doc paths**: docs may not contain `/home/<user>`, `/Users/`,
  `C:\Users`, or this machine's repo root; use `<repo-root>`, `~`, or relative
  paths.
- **Import boundary**: modules under `cli.py`, `mcp/`, `graph/`, `app/` must not
  import `core.casefile` and must not reference `tcr.py` except via
  `ops.runner`. Ledger access goes through `ops/` only.
- **Lazy optional imports**: optional-extra packages (`langgraph`, `langchain*`,
  `llama_index*`, `qdrant_client`, `mem0*`, `docling`, `ocrmypdf`, `fitz`,
  `playwright`, `scrapy`, `trafilatura`, `mcp`, `sentence_transformers`,
  `diskcache`) never at module top level in base-import-reachable code; runtime
  subprocess check: importing `cli` leaves them out of
  `sys.modules`.
- **Network ban**: `socket`, `urllib.request`, `http.client`, `requests`,
  `httpx`, `aiohttp` allowed only in `src/adapters/io/acquisition/`,
  `deployment/`, and the documented `tcr.py` ingest path.
- **Env vars**: registry at `docs/registry/env_vars.json` (name, purpose,
  prefix-class, default, scope). Approved prefixes: `CRK_`, `OLLAMA_`,
  `SEARXNG_`, plus documented singletons (`HF_HOME`, `TRANSFORMERS_CACHE`).
  Discovered-but-undocumented or dynamic (non-literal) keys fail.
- **SaaS/provider denylist**: `langsmith`, `LANGCHAIN_TRACING`,
  `LANGCHAIN_API_KEY`, `smith.langchain.com`, `pinecone`, `weaviate.io`,
  `api.openai.com`, `api.anthropic.com`, `generativelanguage.googleapis`,
  `wandb`, `sentry.io` — banned in `src/`, `deployment/`, `pyproject.toml`,
  skills; allowlist constant for explicitly approved mentions (docs explaining
  the policy are exempt by path).
- **Secret floor** (stdlib regex, always-on): AWS key IDs, PEM private-key
  blocks, `api_key`/`token`/`secret` assignments with high-entropy literals,
  GitHub/Slack token shapes. gitleaks (full ruleset) runs in the audit lane;
  scan excludes gitignored case workspaces, includes fixtures/docs/scripts.
- **License policy**: allowlist MIT, BSD-2/3, Apache-2.0, PSF, ISC, MPL-2.0;
  denylist GPL/AGPL/SSPL (fail); unknown → report for manual review. Scope:
  installed optional-extra dependency trees (runtime core has zero deps).
- **Branch types**: `gov/*`, `ci/*`, `feat/*`, `fix/*`, `docs/*`, `test/*`,
  `chore/*` plus existing `dev`/`canary`/`main` gates. `docs/*` may skip
  integration; everything runs governance + smoke minimum. Enforced in
  `branch_gate.py` (extended) and mirrored in CI.
- **Data-safety gate semantics** (per design review): public-output commands
  fail when required audits are *missing* or report *blocker-grade* issues —
  not when a legitimate, documented contradiction exists. Preserved uncertainty
  is a feature; the gate checks the audit ran and blockers are resolved.
- **Reproducible release** (pragmatic definition): build sdist+wheel twice with
  `SOURCE_DATE_EPOCH` pinned; artifact content listings and file hashes must
  match modulo embedded timestamps.

## 6. Branch map (one branch per goal; deps →)

| # | Branch | Delivers | Depends on |
|---|---|---|---|
| 0 | (main, preflight) | register `criminal-research` template, commit WIP tree green | — |
| 1 | `gov/tooling-baseline` | manifest, fetcher, `governance` extra, make/moon audit-lane targets, `.gitleaks.toml`, LICENSE | — |
| 2 | `gov/repo-shape-naming` | vague-dir denylist, README coverage, generic-doc-path tests | — |
| 3 | `gov/import-boundaries` | import-boundary, lazy-import, network-ban tests | — |
| 4 | `gov/env-provider-policy` | env-var registry + test, SaaS denylist test | — |
| 5 | `gov/security-scans` | secret-floor pytest, gitleaks wiring | 1 |
| 6 | `gov/data-safety-gates` | fixture schema validation, export round-trip privacy/provenance tests, negative fixture, aggregate gate | — |
| 7 | `gov/docs-drift` | internal link checker, CLI-help drift, runbook coverage | — |
| 8 | `gov/packaging-policy` | extras-grouping test, license check, fresh-build check | 1 |
| 9 | `ci/github-actions` | `ci.yml`/`audit.yml`/`release.yml` thin make-callers, branch-gate extension, CI/make parity test | 1, all gov/* merged |
| 10 | `ci/release-readiness` | CHANGELOG + gate, reproducible-build check, SBOM in release | 1, 9 |

Branches 2, 3, 4, 6, 7 are independent and parallelizable across agents.

## 7. Owner decisions (defaults applied unless overridden)

1. **LICENSE**: none exists; program adds MIT (default recommendation) —
   swap file content if you prefer Apache-2.0.
2. **External link checking**: non-blocking scheduled job only (PRs never gated
   on third-party uptime).
3. **pip-audit**: accepted as the one network-dependent check; skips with a
   warning offline.
4. **Ownership notes**: per-dir README purpose line (existing pattern), not a
   CODEOWNERS matrix, until there are multiple maintainers.
