# Governance & CI Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce the full governance program (structure, boundaries, security/local-only, data safety, docs drift, packaging, CI/release) as locally runnable pytest gates plus a pinned external-tool audit lane and thin CI mirrors.

**Architecture:** Extend the existing `tests/quality/governance/` stdlib-pytest suite for everything statically decidable; acquire and pin external tools (gitleaks, lychee, pip-audit, pip-licenses, cyclonedx-bom) behind `make`/moon targets in an isolated audit lane; add GitHub Actions workflows that only call those targets, mirroring the existing moon `branch_gate.py`.

**Tech Stack:** Python stdlib (`ast`, `tokenize`, `json`, `re`, `subprocess`), pytest, moonrepo tasks, GitHub Actions, gitleaks v8.30.1, lychee 0.23.0, pip-audit 2.10.1, pip-licenses 5.5.5, cyclonedx-bom 7.3.0.

Spec: `docs/superpowers/specs/2026-07-02-governance-hardening-spec.md` (policies, pins, decisions — normative).

## Global Constraints

- Repo-shape governance applies to everything you add outside `.agents/`, `data/`, `docs/superpowers/`: 1-4 direct files and 0-3 child dirs per governed dir; every governed file < 200 non-comment LOC (`tests/quality/governance/test_repository_shape.py`). `.github/`, `src/case_builder/`, and `tests/` are all governed by the same shape rule.
- Every new `src/case_builder/` package dir with `__init__.py` needs `README.md` (enforced by `tests/quality/governance/test_repository_shape.py`).
- No new required dependencies: core stays stdlib. New tooling goes in the `governance` optional extra or as fetched pinned binaries.
- Governance tests must not use the network. Audit-lane targets may; they must degrade with a clear skip message offline.
- Every CI job step must be expressible as a `make <target>` (which delegates to `moon run crk:<task>`).
- Test files follow existing conventions: `tests/helpers.py` `KIT_ROOT`/`TCR_PATH`, markers auto-applied by directory, `git ls-files` for tracked-file enumeration.
- Conventional commit messages (`test:`, `feat:`, `chore:`, `ci:`, `docs:`); commit after every green step; end commits with the Claude Code trailer.
- New policy constants (denylists, allowlists) live at module top of their test file with a comment pointing at the spec.
- Branch names exactly as listed; branch from up-to-date `main`; merge back with `--no-ff`.

---

## Phase 0 — Preflight (on `main`, before any branch)

**Files:**
- Modify: `docs/registry/templates/extraction.json` (register `criminal-research` template if absent)
- Track: `.agents/skills/criminal-research/` (4 files, currently untracked)
- Commit: all currently modified tracked files (user WIP)

**Steps:**

- [ ] **Step 0.1:** Run `.venv/bin/python -m pytest tests/quality/governance -x -q` on the dirty tree. Record result.
- [ ] **Step 0.2:** If `criminal-research` is not in the registry template shard, add it to `docs/registry/templates/extraction.json` following the existing entry format (id `criminal-research`, template file path under the skill's assets — mirror an existing entry, confirm the referenced template file exists; if the skill has no template file yet, add the skill dir WITHOUT registry changes and verify `test_skill_docs_only_reference_known_template_and_lane_ids` still passes since the doc references template `criminal-research`).
- [ ] **Step 0.3:** `git add -A && .venv/bin/python -m pytest tests/quality/governance -q` — must be green before committing.
- [ ] **Step 0.4:** Commit: `chore: land criminal-research skill WIP and doc edits`
- [ ] **Step 0.5:** Commit spec + this plan: `docs: add governance hardening spec and plan`

## Phase 1 — Branch `gov/tooling-baseline` (external resources FIRST)

**Files:**
- Create: `deployment/tooling/manifest.json`, `deployment/tooling/README.md`
- Create: `deployment/scripts/tools/fetch_governance_tools.py` (stdlib fetch+sha256-verify → gitignored `deployment/tooling/bin/`)
- Create: `.gitleaks.toml`, `LICENSE` (MIT), 
- Modify: `pyproject.toml` (add `governance` extra), `moon.yml` + `Makefile` (targets: `audit-secrets`, `audit-deps`, `audit-licenses`, `audit-links`, `sbom`, `build-dist`), `.gitignore` (`deployment/tooling/bin/`)
- Test: `tests/quality/governance/test_tooling_manifest.py`

**Interfaces (later phases consume):**
- `make audit-secrets` → runs gitleaks via fetched binary; exit 0 clean.
- `make audit-deps` → `pip-audit`; prints `SKIP (offline)` and exits 0 when the advisory DB is unreachable.
- `manifest.json` shape: `{"tools": {"gitleaks": {"version": "8.30.1", "sha256": {"linux_x64": "<real hash>"}, "url_template": "..."}, ...}, "python_pins": {"pip-audit": "2.10.1", "pip-licenses": "5.5.5", "cyclonedx-bom": "7.3.0"}}`

**Steps:**

- [ ] **Step 1.1:** Write failing test `tests/quality/governance/test_tooling_manifest.py`:

```python
"""Governance: pinned tooling manifest stays consistent with pyproject and make targets."""
import json, re
from tests.helpers import KIT_ROOT

MANIFEST = KIT_ROOT / "deployment" / "tooling" / "manifest.json"
REQUIRED_TOOLS = {"gitleaks", "lychee"}
REQUIRED_PYTHON_PINS = {"pip-audit", "pip-licenses", "cyclonedx-bom"}
AUDIT_TARGETS = {"audit-secrets", "audit-deps", "audit-licenses", "audit-links", "sbom", "build-dist"}

def test_manifest_pins_tools_with_checksums():
    data = json.loads(MANIFEST.read_text())
    assert REQUIRED_TOOLS <= set(data["tools"])
    for name, tool in data["tools"].items():
        assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", tool["version"]), name
        assert tool["sha256"], f"{name} missing checksums"

def test_python_pins_match_governance_extra():
    data = json.loads(MANIFEST.read_text())
    pyproject = (KIT_ROOT / "pyproject.toml").read_text()
    for pkg, version in data["python_pins"].items():
        assert f"{pkg}=={version}" in pyproject, f"{pkg} pin drift"
    assert REQUIRED_PYTHON_PINS <= set(data["python_pins"])

def test_make_exposes_audit_lane_targets():
    makefile = (KIT_ROOT / "Makefile").read_text()
    for target in AUDIT_TARGETS:
        assert f"\n{target}:" in makefile, f"make target {target} missing"
```

- [ ] **Step 1.2:** Run `pytest tests/quality/governance/test_tooling_manifest.py -q` — expect FAIL (no manifest).
- [ ] **Step 1.3:** Create `manifest.json` with real upstream sha256 checksums (fetch release checksums for gitleaks v8.30.1 and lychee 0.23.0 from their GitHub releases — network step, do it now), `governance` extra in pyproject (`pip-audit==2.10.1`, `pip-licenses==5.5.5`, `cyclonedx-bom==7.3.0`, `build>=1.2`), Makefile+moon targets delegating per existing pattern (`moon run crk:<task>`; moon tasks call `deployment/scripts/tools/venv_exec.py` or the fetcher).
- [ ] **Step 1.4:** Write `fetch_governance_tools.py`: reads manifest, downloads each tool for the host platform into `deployment/tooling/bin/`, verifies sha256, `chmod +x`; idempotent; `--offline` flag exits 0 with a notice when binaries already present. Keep < 200 non-comment LOC.
- [ ] **Step 1.5:** Run the fetcher for real: `python deployment/scripts/tools/fetch_governance_tools.py` — binaries verified present. Then `pip install -e '.[governance]'` into `.venv`. **This is the resource-acquisition gate: do not proceed to later phases until both succeed.**
- [ ] **Step 1.6:** `.gitleaks.toml`: default ruleset + `[allowlist]` paths for `data/cases/`, `data/exports/` (gitignored anyway), synthetic fixture pseudo-data. Run `make audit-secrets` on the repo — triage any hits (expected: none; fixtures are synthetic).
- [ ] **Step 1.7:** Add `LICENSE` (MIT, copyright 2026 StonedAcademia contributors).
- [ ] **Step 1.8:** Full check: `pytest tests/quality/governance -q && make check` — green.
- [ ] **Step 1.9:** Commits (split logically): `feat(tooling): add pinned governance tool manifest and fetcher`, `chore: add gitleaks config and MIT license`, `feat(tooling): add audit-lane make and moon targets`.

## Phase 2 — Branch `gov/repo-shape-naming`

**Files:**
- Create: `tests/quality/governance/test_path_policies.py`

**Steps:**

- [ ] **Step 2.1:** Write the test (passes on clean repo — verify enforcement in Step 2.2):

```python
"""Governance: path naming, README coverage, and generic doc paths (spec §5)."""
import re, subprocess
from tests.helpers import KIT_ROOT

VAGUE_DIR_NAMES = {"misc", "old", "temp", "tmp", "stuff", "util", "utils",
                   "helpers", "common", "shared", "new", "junk", "scratch"}
APPROVED_VAGUE_DIRS: set[str] = set()   # repo-relative paths, explicit sign-off only
MACHINE_ROOT_RE = re.compile(r"(/home/[a-z_][a-z0-9_-]*/|/Users/|C:\\Users)")
README_REQUIRED_ROOTS = ("deployment/scripts", "docs/guides", "docs/registry")

def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=KIT_ROOT, check=True,
                         capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line]

def test_no_vague_directory_names():
    offenders = set()
    for path in tracked_files():
        parts = path.split("/")[:-1]
        for depth, part in enumerate(parts, 1):
            rel = "/".join(parts[:depth])
            if part.lower() in VAGUE_DIR_NAMES and rel not in APPROVED_VAGUE_DIRS:
                offenders.add(rel)
    assert not offenders, f"vague directory names (spec §5): {sorted(offenders)}"

def test_docs_use_generic_paths_only():
    offenders = []
    for path in tracked_files():
        if not (path.startswith("docs/") or path == "README.md") or path.startswith("docs/superpowers/"):
            continue
        if not path.endswith((".md", ".json", ".yml", ".yaml", ".svg")):
            continue
        for lineno, line in enumerate((KIT_ROOT / path).read_text(errors="replace").splitlines(), 1):
            if MACHINE_ROOT_RE.search(line):
                offenders.append(f"{path}:{lineno}")
    assert not offenders, f"machine-specific paths in docs: {offenders}"

def test_workflow_dirs_have_readmes():
    dirs = {"/".join(p.split("/")[:-1]) for p in tracked_files()
            if p.startswith(README_REQUIRED_ROOTS) and "/" in p}
    missing = sorted(d for d in dirs if not (KIT_ROOT / d / "README.md").exists()
                     and any(f"{d}/" in p or p.startswith(f"{d}/") for p in tracked_files()))
    assert not missing, f"dirs missing README.md ownership note: {missing}"
```

- [ ] **Step 2.2:** Prove enforcement: `mkdir docs/misc && touch docs/misc/x.md && git add docs/misc` → run test → expect FAIL naming `docs/misc`; then `git rm -r --cached docs/misc && rm -rf docs/misc` → PASS. Do the same spot-check for a doc containing `/home/tester/`.
- [ ] **Step 2.3:** Fix any real offenders the new tests catch (add READMEs where missing — one-line purpose/ownership note per spec §7.4).
- [ ] **Step 2.4:** `pytest tests/quality/governance -q` green. Commit: `test(governance): enforce path naming, doc path genericity, and README coverage`

## Phase 3 — Branch `gov/import-boundaries`

**Files:**
- Create: `tests/quality/governance/test_import_boundaries.py`

**Interfaces:** policy constants exactly as spec §5 (frontend roots: `src/case_builder/cli.py`, `src/case_builder/adapters/interfaces/mcp/`, `src/case_builder/pipeline/graph/`, `src/case_builder/pipeline/app/`; forbidden: `case_builder.core.casefile`, direct `tcr.py` refs outside `ops/runner.py`; optional packages list; network modules list with allowed roots `src/case_builder/adapters/io/acquisition/`).

**Steps:**

- [ ] **Step 3.1:** Write the test:

```python
"""Governance: frontend->ops import boundary, lazy optional imports, network ban (spec §5)."""
import ast, subprocess, sys
from pathlib import Path
from tests.helpers import KIT_ROOT

SRC = KIT_ROOT / "src" / "case_builder"
FRONTEND_ROOTS = [SRC / "cli.py", SRC / "mcp", SRC / "graph", SRC / "app"]
FORBIDDEN_FOR_FRONTENDS = {"case_builder.core.casefile"}
OPTIONAL_PACKAGES = {"langgraph", "langchain", "langchain_ollama", "llama_index",
                     "qdrant_client", "mem0", "docling", "ocrmypdf", "fitz",
                     "playwright", "scrapy", "trafilatura", "mcp",
                     "sentence_transformers", "diskcache"}
NETWORK_MODULES = {"socket", "requests", "httpx", "aiohttp"}
NETWORK_ATTR_MODULES = {"urllib": {"request"}, "http": {"client"}}
NETWORK_ALLOWED = {SRC / "acquisition"}

def iter_py(root: Path):
    yield from ([root] if root.is_file() else sorted(root.rglob("*.py")))

def imports_of(path: Path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names: yield a.name, node.lineno, node
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module
            if node.level:  # resolve relative to absolute within case_builder
                pkg = path.relative_to(SRC.parent).parts[:-node.level]
                mod = ".".join((*pkg, node.module))
            yield mod, node.lineno, node

def top_level(node, tree_body_ids):  return id(node) in tree_body_ids

def test_frontends_never_touch_ledger_internals():
    offenders = []
    for root in FRONTEND_ROOTS:
        for path in iter_py(root):
            for mod, lineno, _ in imports_of(path):
                if any(mod == f or mod.startswith(f + ".") for f in FORBIDDEN_FOR_FRONTENDS):
                    offenders.append(f"{path.relative_to(KIT_ROOT)}:{lineno} imports {mod}")
    assert not offenders, offenders

def test_tcr_script_only_referenced_via_ops_runner():
    offenders = [str(p.relative_to(KIT_ROOT)) for root in FRONTEND_ROOTS for p in iter_py(root)
                 if "tcr.py" in p.read_text()]
    assert not offenders, f"frontends reference tcr.py directly: {offenders}"

def test_optional_packages_import_lazily():
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text())
        body_ids = {id(n) for n in tree.body}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and id(node) in body_ids:
                names = [a.name for a in node.names] if isinstance(node, ast.Import) \
                        else [node.module or ""]
                for name in names:
                    if name.split(".")[0] in OPTIONAL_PACKAGES:
                        offenders.append(f"{path.relative_to(KIT_ROOT)}:{node.lineno} top-level {name}")
    assert not offenders, offenders

def test_base_cli_import_pulls_no_optional_packages():
    code = ("import sys, case_builder.cli; "
            "hits = sorted({m.split('.')[0] for m in sys.modules} & "
            f"{OPTIONAL_PACKAGES!r}); "
            "print(','.join(hits)); sys.exit(1 if hits else 0)")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          cwd=KIT_ROOT, env={"PYTHONPATH": str(KIT_ROOT / "src"), "PATH": "/usr/bin:/bin"})
    assert proc.returncode == 0, f"eager optional imports: {proc.stdout} {proc.stderr}"

def test_network_modules_confined_to_acquisition():
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        if any(path.is_relative_to(a) for a in NETWORK_ALLOWED): continue
        for mod, lineno, _ in imports_of(path):
            head, *rest = mod.split(".")
            if head in NETWORK_MODULES or (head in NETWORK_ATTR_MODULES
                                           and rest and rest[0] in NETWORK_ATTR_MODULES[head]):
                offenders.append(f"{path.relative_to(KIT_ROOT)}:{lineno} imports {mod}")
    assert not offenders, offenders
```

- [ ] **Step 3.2:** Run it. Expect surprises (e.g., `mcp` package imports at top level inside `src/case_builder/adapters/interfaces/mcp/` — that is the *frontend for* the extra, so refine: allow an optional package at top level inside the subsystem dir that exists only for it: `mcp/` may import `mcp`, `graph/` may import `langgraph` ONLY inside `try/except ImportError` — detect by checking the import's enclosing `Try` node; parsing note: walk `tree.body` `ast.Try` handlers too). Iterate until the rules encode reality without weakening the boundary; every exemption gets a comment.
- [ ] **Step 3.3:** Prove each test can fail (temporarily add `import case_builder.core.casefile` to `cli.py`, a top-level `import langgraph` to `ops/case.py`, `import requests` to `models/state.py` → each test fails → revert).
- [ ] **Step 3.4:** Full suite green; commit: `test(governance): enforce ops boundary, lazy optional imports, and network confinement`

## Phase 4 — Branch `gov/env-provider-policy`

**Files:**
- Create: `docs/registry/env_vars.json`, `tests/quality/governance/test_env_and_providers.py`

**Interfaces:** registry entry shape `{"name": "CRK_MODEL", "purpose": "...", "scope": "runtime|deployment|ci", "default": "...", "prefix_class": "CRK_"}`; approved prefixes and SaaS denylist verbatim from spec §5.

**Steps:**

- [ ] **Step 4.1:** Build `docs/registry/env_vars.json` from the survey's inventory: `CRK_CASES_ROOT, CRK_SKILL_ROOT, CRK_MODEL, CRK_SEARXNG_URL, CRK_QDRANT_URL, CRK_QDRANT_HOST, CRK_QDRANT_PORT, CRK_EMBED_MODEL, CRK_MEM0_LLM_PROVIDER, CRK_MEM0_LLM_MODEL, CRK_EMBEDDER_PROVIDER, CRK_HOOK_BRANCH, CRK_REPO_ROOT, OLLAMA_HOST, SEARXNG_BASE_URL, HF_HOME, TRANSFORMERS_CACHE` — each with real purpose/default read from the code (`src/case_builder/core/config.py`, `deployment/`).
- [ ] **Step 4.2:** Write the test: AST scan of `src/**/*.py` + `.agents/skills/*/scripts/*.py` for `os.environ[...]`/`os.environ.get(...)`/`os.getenv(...)`; regex scan of `deployment/**` shell/yaml/compose for `${VAR}`/`environment:` keys. Assert (a) every discovered literal key is registered, (b) non-literal env keys are absent, (c) every registered key matches an approved prefix or is an approved singleton, (d) every registered `runtime`-scope key is actually read somewhere (no dead registry entries).
- [ ] **Step 4.3:** Same file, SaaS denylist test: case-insensitive substring scan of tracked files under `src/`, `deployment/`, `.agents/skills/`, plus `pyproject.toml` for the spec §5 denylist terms; exempt paths: this test file, the spec/plan docs. Prove it fails on a planted `import langsmith`.
- [ ] **Step 4.4:** Green; commits: `feat(registry): add canonical env var registry`, `test(governance): enforce env var registry and local-only provider policy`

## Phase 5 — Branch `gov/security-scans` (after Phase 1 merges)

**Files:**
- Create: `tests/quality/governance/test_secret_floor.py`

**Steps:**

- [ ] **Step 5.1:** Write the stdlib secret-floor test: regexes for AWS key IDs (`AKIA[0-9A-Z]{16}`), PEM blocks (`-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----`), GitHub tokens (`ghp_[A-Za-z0-9]{36}`, `github_pat_`), Slack (`xox[bpars]-`), and assignments `(api_key|apikey|secret|token|password)\s*[=:]\s*["'][A-Za-z0-9+/_-]{20,}["']` over all tracked text files; allowlist: test file itself, gitleaks config, obvious placeholders (`<...>`, `changeme`, `example`, `synthetic`).
- [ ] **Step 5.2:** Plant `aws_key = "AKIA` + 16 caps in a scratch tracked file → FAIL → remove. Suite green.
- [ ] **Step 5.3:** Verify `make audit-secrets` (gitleaks from Phase 1) runs clean; wire it into `branch_gate.py`'s canary/main target lists.
- [ ] **Step 5.4:** Commit: `test(governance): add stdlib secret floor and gate gitleaks in canary/main`

## Phase 6 — Branch `gov/data-safety-gates`

**Files:**
- Create: `tests/quality/governance/test_data_safety.py` (schema validation of fixtures — stdlib json + `jsonschema` if dev extra present, else structural checks)
- Create: `tests/runtime/integration/operations/exports/test_safety.py` (round-trips; integration because it shells out to tcr.py)
- Create: `data/examples/unsafe_case_fixture/` (negative fixture: a claim with `public_export: false`, a private address, a minor's name, a claim with no `source_ids`, an automation co-mention with high confidence — each individually unsafe)
- Modify: `.agents/skills/truecrime-cult-research/scripts/tcr.py` — aggregate gate: public-output commands (`export-*` without `--include-private`) run `audit-public-export` + `audit-privacy-redactions` + blocker-grade contradiction/independence checks first; refuse with actionable message on blockers. **Delegate this edit to Codex** (it has already mapped tcr.py's audit internals); keep the diff minimal and stdlib-only.

**Steps:**

- [ ] **Step 6.1:** `test_data_safety.py`: every `data/examples/*/records/*.jsonl` line parses and validates against its `docs/schemas/<record_type>.schema.json`; every claim in the synthetic case has `source_ids`, `confidence`, `status`, and a resolvable reliability-grade path; automation co-mentions are `status: unverified` + `public_export: false`.
- [ ] **Step 6.2:** Build the unsafe fixture. Run existing `tcr.py validate` + `audit-public-export` against it — confirm current behavior (should already flag some; record which unsafe records get through: those are the gaps).
- [ ] **Step 6.3:** `test_export_safety.py`: (a) export synthetic case public → assert output contains no `public_export: false` records, no address/contact/minor fields, no claims lacking source IDs; (b) export unsafe fixture public → assert the command FAILS (aggregate gate) and names each blocker; (c) `--include-private` on synthetic case still works and is labeled internal.
- [ ] **Step 6.4:** Run 6.3 → expect (b) to FAIL until the tcr.py aggregate gate lands. Dispatch Codex for the tcr.py change with the failing test as the acceptance criterion.
- [ ] **Step 6.5:** All green incl. full governance + integration. Commits: `test(governance): validate fixture schemas and claim provenance`, `feat(tcr): aggregate public-output safety gate`, `test(integration): export round-trip privacy gates with negative fixture`

## Phase 7 — Branch `gov/docs-drift`

**Files:**
- Create: `tests/quality/governance/test_docs_links.py`, `tests/quality/governance/test_runbook_coverage.py`

**Steps:**

- [ ] **Step 7.1:** `test_docs_links.py`: for every tracked `*.md`, resolve relative links/images (`[..](path)`, excluding `http(s)://`, `mailto:`, `#anchors`) against the tree; assert all targets exist. Also assert intra-doc anchors referenced as `file.md#heading` match a heading slug in the target.
- [ ] **Step 7.2:** `test_runbook_coverage.py`: enumerate public commands — `cr-kit` subcommands via `argparse` introspection (`python -m case_builder.cli --help` subprocess, parse the subcommand list), `tcr.py` subcommands the same way, `make docker-*` targets from the Makefile — assert each appears in at least one file under `docs/guides/runbooks/`. Maintain an explicit `RUNBOOK_EXEMPT` set (internal/dev-only commands) with justification comments.
- [ ] **Step 7.3:** CLI-help drift: extend the existing pattern from `test_lanes_json.py` — any doc that embeds a `--help` snippet (marked by a `<!-- cli-help: <command> -->` comment convention; add the convention to the two docs that quote CLI help) must match live `--help` output. If no docs quote help verbatim today, add the convention doc-side where snippets exist, else record N/A in the commit message.
- [ ] **Step 7.4:** Fix every broken link / uncovered command this reveals (expect several — budget for it). Green. Commits: `test(governance): internal link and anchor checker`, `test(governance): runbook coverage for public commands`, `docs: repair links and runbook gaps found by new gates`

## Phase 8 — Branch `gov/packaging-policy` (after Phase 1 merges)

**Files:**
- Create: `tests/quality/governance/test_packaging_policy.py`, `deployment/scripts/checks/license_policy.py` (reads `pip-licenses` JSON, applies spec §5 allow/deny), `deployment/scripts/checks/fresh_build.py` (temp venv, `pip install build`, `python -m build` from `git archive` of HEAD, import-check the wheel)

**Steps:**

- [ ] **Step 8.1:** `test_packaging_policy.py`: parse `pyproject.toml` (tomllib): core `dependencies == []`; every extra's packages map to its capability (assert known groups exactly: dev/agentic/llm/mcp/web-local/documents/retrieval/memory-local/governance; no new extra without a spec edit — encode current grouping as the expected constant); `LICENSE` file exists and `project.license` declared; console scripts unchanged.
- [ ] **Step 8.2:** Wire `make audit-licenses` → `license_policy.py` (skip-with-notice if pip-licenses absent) and `make build-dist` → `fresh_build.py`. Run both for real; fix fallout (missing `license` field, MANIFEST gaps).
- [ ] **Step 8.3:** Green. Commits: `test(governance): packaging and extras grouping policy`, `feat(checks): license policy and fresh-build verification scripts`

## Phase 9 — Branch `ci/github-actions` (after 1-8 merged to main)

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/workflows/audit.yml`, `.github/workflows/release.yml` (3 files in `workflows/`; `.github/` gets ≤1 more direct file — budget per repo-shape)
- Modify: `deployment/scripts/checks/branch_gate.py` (extend `BRANCH_TARGETS` with prefix rules: `docs/*` → check+governance; `gov/* test/* chore/*` → check+governance+smoke; `feat/* fix/* ci/*` → check+governance+smoke+test-integration; unknown prefix → full suite)
- Create: `tests/quality/governance/test_ci_parity.py`

**Steps:**

- [ ] **Step 9.1:** `ci.yml`: on PR + push to dev/canary/main; single job matrix `python: [3.10, 3.12]` for `make check test-governance test-smoke`, full `make test` on main only; every `run:` line is a make target; ~60 LOC. `audit.yml`: weekly cron + manual + dependency-file paths trigger; jobs: `make audit-secrets audit-deps audit-licenses audit-links`; `continue-on-error: true` for links; network-permitted lane. `release.yml`: on `v*` tags; `make test build-dist sbom audit-secrets audit-deps` + changelog gate (Phase 10 adds it).
- [ ] **Step 9.2:** `test_ci_parity.py`: parse each workflow YAML with a small stdlib parser (line-regex for `run:` steps is acceptable — no pyyaml dep): assert every `run:` invokes `make <target>` and each target exists in the Makefile; assert `.github` stays within shape budget (belt-and-braces with repo-shape test).
- [ ] **Step 9.3:** Extend `branch_gate.py` + its unit tests (`tests/` has existing coverage of the gate — extend in place). Verify with `CRK_HOOK_BRANCH=gov/example python deployment/scripts/checks/branch_gate.py --dry-run` style invocation (add `--dry-run` printing resolved targets if absent).
- [ ] **Step 9.4:** Push branch, confirm the workflows actually run green on GitHub (this is the one step needing the remote). Commits: `ci: add thin make-calling workflows for ci, audit, release lanes`, `feat(checks): branch-type prefixes in branch gate`, `test(governance): ci/make parity`

## Phase 10 — Branch `ci/release-readiness` (after 9)

**Files:**
- Create: `CHANGELOG.md` (Keep-a-Changelog format, `## [Unreleased]` + backfilled `## [0.1.0]` from git history), `deployment/scripts/checks/release_readiness.py` (asserts: tag matches `pyproject.toml` version, CHANGELOG has a dated section for it, reproducible double-build per spec §5 definition with `SOURCE_DATE_EPOCH`, SBOM emitted per extra + aggregate via cyclonedx-bom)
- Modify: `.github/workflows/release.yml` (call it), `Makefile`/`moon.yml` (`release-check` target)
- Test: `tests/quality/governance/test_release_readiness.py` (CHANGELOG format parses; unreleased section exists; script's tag/version/changelog logic unit-tested with tmp fixtures)

**Steps:**

- [ ] **Step 10.1:** TDD `release_readiness.py` logic via the governance test (feed it tmp pyproject/CHANGELOG/tag combinations; assert pass/fail matrix).
- [ ] **Step 10.2:** Run `make release-check` for real against a throwaway local tag `v0.1.0` — double-build comparison must pass; fix nondeterminism via `SOURCE_DATE_EPOCH` and stable file ordering.
- [ ] **Step 10.3:** Green; commits: `docs: add changelog`, `feat(release): release readiness gate with reproducible build and sbom`

## Delegation map

| Phase | Owner |
|---|---|
| 0, spec/plan upkeep | orchestrator (Fable) |
| 1 | fast-worker (fetcher + manifest mechanical; checksums verified by orchestrator) |
| 2, 5, 7 | fast-worker |
| 3 | deep-reasoner (AST edge cases: relative imports, try/except exemptions) |
| 4 | fast-worker, deep-reasoner reviews the discovery scanner |
| 6 | deep-reasoner (tests) + **Codex** (tcr.py aggregate gate) |
| 8 | fast-worker |
| 9 | deep-reasoner (workflow/gate design) + fast-worker (yaml) |
| 10 | Codex (reproducible-build subtleties) |

Every phase: implementing agent works on the named branch in a worktree, commits at each step, runs `pytest tests/quality/governance -q` + touched suites before each commit; orchestrator reviews the diff, merges `--no-ff` to main, deletes the branch. Phases 2/3/4/6/7 may run in parallel worktrees.
