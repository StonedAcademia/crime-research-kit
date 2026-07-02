# tc-c-kit Skills + Vocabulary Consolidation (Phase 5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `docs/lanes.json` the single source of truth for lane names, extraction templates, adjacent-skill routing, source-type hints, trigger terms, and public-record planning defaults; update repo-local skills and docs so Codex/MCP/CLI users see one coherent operation vocabulary.

**Architecture:** A small `case_builder/lanes/` package reads `docs/lanes.json` with stdlib JSON only. Existing callers keep their public imports (`case_builder.agents.source_lanes.FALLBACK_LANES`, `LANE_TRIGGERS`, `infer_source_lanes`) but those values are derived from the registry. The repo-local `tcr.py` script also loads the registry at startup and derives `EXTRACTION_TEMPLATE_FILES`, `EXTRACTION_TEMPLATE_NOTES`, and `PUBLIC_RECORD_LANES` from it. Skill reference docs that are tabular or index-like are generated from the registry; narrative skill docs reference shared operation names and include CLI fallback examples only as compatibility notes.

**Tech Stack:** Python >=3.10, stdlib JSON/pathlib, pytest. No new runtime dependencies and no change to `[project] dependencies = []`.

## Global Constraints

- Repo root: `<project_root>/`. All paths below are relative to it.
- Modules stay under **200 non-comment LOC**; every package dir under `src/case_builder/` has a `README.md` (enforced by `tests/test_case_builder_structure.py`).
- `docs/lanes.json` is data, not evidence. It never creates case claims, sources, relationships, or public-ready narrative assertions.
- Preserve current safety defaults: route suggestions remain lead-only; unknown or ambiguous lanes fail closed where a CLI/MCP tool is about to act; public exports stay public-safe by default.
- Keep the existing CLI operation names stable. Phase 5 may derive choices from the registry, but it must not rename `draft-extraction`, `plan-public-records`, `review-narrative-readiness`, `audit-privacy-redactions`, or `audit-source-independence`.
- Do not require Phase 4 MCP implementation to run the Phase 5 registry tests. MCP-specific skill text can describe the preferred surface, but tests should not import `mcp`.
- Commit per task, conventional-commit style, ending with:

  ```text
  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```

## Current Duplication To Remove

| Current source | Problem |
| --- | --- |
| `.agents/skills/truecrime-cult-research/scripts/tcr.py` | Hard-codes `EXTRACTION_TEMPLATE_FILES`, `EXTRACTION_TEMPLATE_NOTES`, and `PUBLIC_RECORD_LANES`. |
| `src/case_builder/agents/source_lanes.py` | Hard-codes an overlapping but smaller `LANE_TRIGGERS` map and fallback list. |
| `.agents/skills/public-records-router/references/routing_matrix.md` | Hand-maintained lane/skill/template table that can drift from `tcr.py`. |
| `.agents/skills/*/SKILL.md` | Mixes raw CLI command examples and lane names without a shared operation vocabulary. |
| `docs/skill-api-spec.md` and `README.md` | Repeat supported template names and adjacent-skill routing prose. |

## File Structure (End State)

```text
docs/lanes.json                         # NEW: canonical lane/template registry
docs/schemas/lanes.schema.json          # NEW: lightweight registry schema
src/case_builder/lanes/
  __init__.py
  README.md
  registry.py                           # load_lanes(), lane_names(), infer_lanes(), public_record_plan()
  docs.py                               # render generated lane docs from registry
src/case_builder/agents/source_lanes.py  # MODIFIED: compatibility wrapper over registry
.agents/skills/truecrime-cult-research/scripts/tcr.py
                                        # MODIFIED: derive template and lane constants from registry
.agents/skills/truecrime-cult-research/references/lane_registry.md
                                        # NEW: generated lane index
.agents/skills/public-records-router/references/routing_matrix.md
                                        # MODIFIED: generated from docs/lanes.json
.agents/skills/truecrime-cult-research/SKILL.md
                                        # MODIFIED: tool access + shared op names
.agents/skills/*/SKILL.md               # MODIFIED: adjacent skill operation vocabulary
docs/skill-api-spec.md                  # MODIFIED: points to docs/lanes.json
README.md                               # MODIFIED: points to lane registry and MCP/CLI tool access

New tests:
tests/test_lanes_json.py
tests/test_lanes_registry.py
tests/test_lanes_docs_generation.py
tests/test_skill_docs_tool_access.py
```

Out of scope: new case data schemas, new extraction packet templates, changing existing lane semantics, HTTP/remote MCP transport, and removing `tcr.py`.

---

## Registry Shape

`docs/lanes.json` should be human-readable and sorted by stable lane ID. Use this shape:

```json
{
  "version": 1,
  "fallback_source_lanes": [
    "source-capture",
    "contradiction"
  ],
  "fallback_public_record_lanes": [
    "source-capture",
    "legal-court",
    "corporate",
    "licensing-professional",
    "media-transcript",
    "missing-persons",
    "geographical-location",
    "property-location"
  ],
  "lanes": {
    "legal-court": {
      "label": "Legal and court records",
      "category": "public_record",
      "skill": "legal-court-records",
      "template": "legal-court",
      "template_file": "extraction_packet_legal_court.json",
      "public_record_plan": true,
      "source_lane_inference": true,
      "triggers": ["court", "docket", "filing", "lawsuit", "charge", "judgment", "hearing", "appeal", "bankruptcy"],
      "source_types": ["court_record", "government_record", "news_article"],
      "notes": "Use for dockets, filings, orders, hearings, allegations, denials, and court findings.",
      "tool_ops": {
        "draft_packet": "draft_extraction",
        "plan_records": "plan_public_records"
      }
    }
  },
  "templates": {
    "generic": {
      "template_file": "extraction_packet.json",
      "notes": "Use for general case/source extraction."
    }
  }
}
```

Rules:

- Every key in `lanes` is a canonical lane ID.
- Every lane with `public_record_plan: true` must have `skill`, `template`, `triggers`, `source_types`, and `notes`.
- Every lane with `template` must point to a key in `templates`.
- Every template must point to an existing file under `.agents/skills/truecrime-cult-research/assets/templates/`.
- `category` is one of `public_record`, `support`, or `review`.
- `source_lane_inference: true` means the graph/LLM source-lane surface may suggest this lane from a seed subject.
- `public_record_plan: true` means `plan-public-records --lane <id>` accepts this lane and can generate source queries for it.

Initial lane table:

| Lane | Category | Skill | Template | Public records? | Source inference? |
| --- | --- | --- | --- | --- | --- |
| `legal-court` | `public_record` | `legal-court-records` | `legal-court` | yes | yes |
| `corporate` | `public_record` | `corporate-financial-records` | `corporate` | yes | yes |
| `education` | `public_record` | `educational-path-records` | `education` | yes | yes |
| `licensing-professional` | `public_record` | `licensing-professional-records` | `licensing-professional` | yes | yes |
| `media-transcript` | `public_record` | `media-transcript-intelligence` | `media-transcript` | yes | yes |
| `property-location` | `public_record` | `property-location-records` | `property-location` | yes | yes |
| `missing-persons` | `public_record` | `missing-persons-case` | `missing-persons` | yes | yes |
| `geographical-location` | `public_record` | `geographical-location-intelligence` | `geographical-location` | yes | yes |
| `source-capture` | `support` | `source-capture-preservation` | `source-capture` | yes | yes |
| `identity-resolution` | `support` | `identity-resolution` | `identity-resolution` | yes | no |
| `contradiction` | `review` | `claim-contradiction-audit` | `claim-contradiction` | yes | yes |
| `public-records-router` | `support` | `public-records-router` | `public-records-router` | no | no |
| `foia-open-records` | `review` | `foia-open-records-planning` | `foia-open-records` | yes | yes |
| `narrative-readiness` | `review` | `narrative-readiness-review` | `narrative-readiness` | no | no |
| `privacy-redaction` | `review` | `privacy-redaction-audit` | `privacy-redaction` | no | no |
| `source-independence` | `review` | `source-independence-audit` | `source-independence` | no | no |

Note: `generic` remains a template, not a lane.

---

### Task 1: Canonical `docs/lanes.json` + schema checks

**Files:**
- Create: `docs/lanes.json`
- Create: `docs/schemas/lanes.schema.json`
- Create: `tests/test_lanes_json.py`

**Interfaces:**
- Produces the canonical registry described above.
- Tests validate it without importing package code, so registry data errors are obvious.

- [ ] **Step 1: Write failing tests**

Create tests that assert:

- `docs/lanes.json` exists and parses as JSON.
- `version == 1`.
- `fallback_source_lanes` and `fallback_public_record_lanes` contain only defined lanes.
- All lane IDs and template IDs are lowercase slug strings (`[a-z0-9][a-z0-9-]*`).
- Every lane `template` exists in `templates`.
- Every template file exists under `.agents/skills/truecrime-cult-research/assets/templates/`.
- Every `public_record_plan` lane has non-empty `triggers`, `source_types`, `skill`, and `notes`.
- `generic` is present in `templates` but absent from `lanes`.

Run:

```bash
cd <project_root>/
.venv/bin/python -m pytest tests/test_lanes_json.py -v
```

Expected before implementation: FAIL because `docs/lanes.json` is missing.

- [ ] **Step 2: Add the registry and schema**

Build `docs/lanes.json` from the existing `tcr.py` constants and `agents/source_lanes.py` triggers. Keep current trigger terms unless the source files already disagree; when they disagree, prefer the richer `tcr.py` `PUBLIC_RECORD_LANES` trigger list and note the compatibility impact in the commit message.

The schema is intentionally lightweight. It documents required fields and enum values but does not need to encode every cross-field rule; the pytest file handles those rules.

- [ ] **Step 3: Verify**

Run:

```bash
cd <project_root>/
.venv/bin/python -m pytest tests/test_lanes_json.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/lanes.json docs/schemas/lanes.schema.json tests/test_lanes_json.py
git commit -m "feat(lanes): add canonical lane registry

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Runtime lane registry package

**Files:**
- Create: `src/case_builder/lanes/__init__.py`
- Create: `src/case_builder/lanes/README.md`
- Create: `src/case_builder/lanes/registry.py`
- Modify: `src/case_builder/README.md`
- Test: `tests/test_lanes_registry.py`

**Interfaces:**
- `default_lanes_path(repo_root: Path | None = None) -> Path`
- `load_lanes(path: Path | None = None) -> dict`
- `lane_records(*, public_record_plan: bool | None = None, source_lane_inference: bool | None = None) -> dict[str, dict]`
- `lane_names(...) -> list[str]`
- `template_records() -> dict[str, dict]`
- `fallback_source_lanes() -> list[str]`
- `fallback_public_record_lanes() -> list[str]`
- `lane_triggers(*, source_lane_inference: bool = True) -> dict[str, tuple[str, ...]]`
- `infer_lanes(subject: str | None, explicit_lanes: Sequence[str] | None = None) -> list[str]`
- `public_record_plan(lane: str, subject: str) -> dict`

Implementation rules:

- Use `functools.lru_cache` for the default registry load.
- Return new lists/dicts or immutable tuples so callers cannot mutate cached data.
- `infer_lanes()` should preserve the current behavior for explicit lanes: dedupe and return them. Add a separate `validate_lane_names(lanes, *, public_record_plan=False)` helper for acting tools.
- `public_record_plan()` must raise `ValueError` for unknown lanes and for lanes where `public_record_plan` is false.
- The package import must not import optional LangGraph, MCP, retrieval, or LLM dependencies.

- [ ] **Step 1: Write failing tests**

Cover:

- default path resolves from the repo root.
- fallback lists match `docs/lanes.json`.
- `lane_triggers()` includes the source-lane inference set and excludes `identity-resolution` if `source_lane_inference` is false.
- `infer_lanes("missing person court filing")` returns `missing-persons` and `legal-court`.
- `public_record_plan("legal-court", "Jane Doe")` includes `lane`, `skill`, `template`, `source_types`, `notes`, and generated `suggested_queries`.
- `public_record_plan("narrative-readiness", "Jane Doe")` raises `ValueError`.

- [ ] **Step 2: Implement `case_builder.lanes`**

Keep `registry.py` under 200 non-comment LOC. If it grows, split rendering into `docs.py` in Task 4 rather than adding more code here.

- [ ] **Step 3: Verify**

Run:

```bash
cd <project_root>/
.venv/bin/python -m pytest tests/test_lanes_registry.py tests/test_case_builder_structure.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/case_builder/lanes src/case_builder/README.md tests/test_lanes_registry.py
git commit -m "feat(lanes): load lane registry at runtime

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Rewire source-lane inference and `tcr.py` constants

**Files:**
- Modify: `src/case_builder/agents/source_lanes.py`
- Modify: `.agents/skills/truecrime-cult-research/scripts/tcr.py`
- Test: extend `tests/test_lanes_registry.py`; add focused CLI smoke to `tests/test_lanes_json.py` if needed.

**Interfaces:**
- `case_builder.agents.source_lanes` keeps these compatibility exports:
  - `FALLBACK_LANES`
  - `LANE_TRIGGERS`
  - `infer_source_lanes(subject, explicit_lanes=None)`
- `tcr.py` derives:
  - `EXTRACTION_TEMPLATE_FILES`
  - `EXTRACTION_TEMPLATE_NOTES`
  - `PUBLIC_RECORD_LANES`
  - `argparse` choices for `draft-extraction --template` and `plan-public-records --lane`

Implementation notes:

- `tcr.py` cannot rely on the package being importable when invoked directly from a checkout. Add a small `load_lanes_registry()` helper inside `tcr.py` that looks for `docs/lanes.json` at:
  - the kit root inferred from `.agents/skills/truecrime-cult-research/scripts/tcr.py`
  - `Path.cwd() / "docs" / "lanes.json"`
  - `Path.cwd() / "tc-c-kit" / "docs" / "lanes.json"`
- If `docs/lanes.json` is missing, fail with a clear `SystemExit` during commands that need lanes/templates. Do not silently fall back to stale hard-coded maps.
- Keep `generic` available as a `draft-extraction --template` choice.

- [ ] **Step 1: Write failing tests**

Add tests that assert:

- `source_lanes.LANE_TRIGGERS` equals registry trigger data for `source_lane_inference` lanes.
- `source_lanes.FALLBACK_LANES` equals `fallback_source_lanes`.
- `tcr.py draft-extraction --help` includes all template names from `docs/lanes.json`.
- `tcr.py plan-public-records --help` includes all `public_record_plan` lane names and excludes non-planning lanes such as `narrative-readiness`.

- [ ] **Step 2: Implement rewiring**

Replace hard-coded lane maps in `source_lanes.py` with imports from `case_builder.lanes.registry`.

In `tcr.py`, keep the derived constants near the current constants so the rest of the file can remain mostly unchanged.

- [ ] **Step 3: Verify**

Run:

```bash
cd <project_root>/
.venv/bin/python -m pytest tests/test_lanes_json.py tests/test_lanes_registry.py tests/test_case_builder.py -v
.venv/bin/python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction --help >/tmp/trcr-draft-help.txt
.venv/bin/python .agents/skills/truecrime-cult-research/scripts/tcr.py plan-public-records --help >/tmp/trcr-plan-help.txt
```

- [ ] **Step 4: Commit**

```bash
git add src/case_builder/agents/source_lanes.py .agents/skills/truecrime-cult-research/scripts/tcr.py tests/test_lanes_json.py tests/test_lanes_registry.py
git commit -m "refactor(lanes): derive routing and template choices from registry

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Generate lane reference docs

**Files:**
- Create: `src/case_builder/lanes/docs.py`
- Create: `.agents/skills/truecrime-cult-research/references/lane_registry.md`
- Modify: `.agents/skills/public-records-router/references/routing_matrix.md`
- Test: `tests/test_lanes_docs_generation.py`

**Interfaces:**
- `render_lane_registry_markdown(registry: dict) -> str`
- `render_routing_matrix_markdown(registry: dict) -> str`
- Optional CLI entry point: `python -m case_builder.lanes.docs --check` and `--write`

Generated docs rules:

- Generated files start with:

  ```text
  <!-- Generated from docs/lanes.json; edit the registry, not this table. -->
  ```

- `lane_registry.md` includes all lanes and templates, grouped by category.
- `routing_matrix.md` includes only `public_record_plan: true` lanes because it powers `public-records-router`.
- Generated tables include lane, skill, template, use-for/notes, and public-safety note where available.

- [ ] **Step 1: Write failing tests**

Tests should render expected output from `docs/lanes.json` and compare it byte-for-byte against the checked-in generated docs.

- [ ] **Step 2: Implement renderer and generated docs**

Keep `docs.py` under 200 non-comment LOC. Prefer simple string assembly with sorted registry keys; no markdown dependency.

- [ ] **Step 3: Verify**

Run:

```bash
cd <project_root>/
.venv/bin/python -m pytest tests/test_lanes_docs_generation.py tests/test_case_builder_structure.py -v
.venv/bin/python -m case_builder.lanes.docs --check
```

- [ ] **Step 4: Commit**

```bash
git add src/case_builder/lanes/docs.py .agents/skills/truecrime-cult-research/references/lane_registry.md .agents/skills/public-records-router/references/routing_matrix.md tests/test_lanes_docs_generation.py
git commit -m "docs(lanes): generate lane reference tables

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Update skill docs to shared operation vocabulary

**Files:**
- Modify: `.agents/skills/truecrime-cult-research/SKILL.md`
- Modify: adjacent `.agents/skills/*/SKILL.md` files whose workflows mention direct packet commands
- Test: `tests/test_skill_docs_tool_access.py`

**Tool access language to add to `truecrime-cult-research/SKILL.md`:**

```markdown
## Tool access

Prefer MCP tools when `trcr-mcp` is registered:

| Workflow need | MCP operation | CLI fallback |
| --- | --- | --- |
| List/open cases | `list_cases`, `case_info` | inspect `data/cases/<case>/case.json` only when tooling is unavailable |
| Read records/source text | `get_records`, `get_source_text` | use `trcr-case-builder query-case` or the source files through repo tooling |
| Register sources | `ingest_url`, `add_source` | `tcr.py ingest-url`, `tcr.py add-source` |
| Draft packets | `draft_extraction` | `tcr.py draft-extraction --template <template>` |
| Save staged packets | `save_extraction_packet` | write reviewed JSON under `staging/extractions/` through repo tooling |
| Import canonical records | `import_extraction(confirm=true)` after explicit user approval | `tcr.py import-extraction` after explicit user approval |
| Public exports | `export_manim`, `export_case_charts`, `export_analysis_charts` | matching `tcr.py export-*` commands |

Lane and template names come from `docs/lanes.json`; generated reference tables
live in `references/lane_registry.md` and
`public-records-router/references/routing_matrix.md`.
```

Adjacent skill update pattern:

- Replace command-first wording like "Use `draft-extraction --template media-transcript`" with "Use operation `draft_extraction` with template `media-transcript`; CLI fallback: `tcr.py draft-extraction ... --template media-transcript`."
- Keep concrete CLI examples where they help humans, but make the operation name the source of truth.
- Add a single sentence to each adjacent skill: "Lane/template metadata is generated from `docs/lanes.json`; do not invent new lane IDs in this skill doc."
- Do not weaken any safety rule, redaction rule, or "do not infer" language.

- [ ] **Step 1: Write failing tests**

Tests should assert:

- Main skill has a `## Tool access` section.
- Main skill references `trcr-mcp`, `import_extraction(confirm=true)`, and `docs/lanes.json`.
- Every skill named by a lane in `docs/lanes.json` has either a `template <id>` mention or no template because it is a planning-only skill.
- No skill doc mentions a `--template <id>` that is absent from the registry.
- No skill doc mentions `--lane <id>` that is absent from the registry.

- [ ] **Step 2: Update docs**

Use targeted edits. Do not rewrite adjacent skills wholesale; they contain domain-specific safety rules.

- [ ] **Step 3: Verify**

Run:

```bash
cd <project_root>/
.venv/bin/python -m pytest tests/test_skill_docs_tool_access.py -v
```

- [ ] **Step 4: Commit**

```bash
git add .agents/skills tests/test_skill_docs_tool_access.py
git commit -m "docs(skills): align workflows with shared lane operations

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Public docs and API spec alignment

**Files:**
- Modify: `docs/skill-api-spec.md`
- Modify: `README.md`
- Modify: `docs/mcp-server.md` if Phase 4 has already landed

**Required updates:**

- `docs/skill-api-spec.md` says lane/template vocabulary lives in `docs/lanes.json`; generated human tables live in skill references.
- The list of `draft-extraction --template` names is either generated in prose from `docs/lanes.json` during docs generation or replaced by a pointer to `docs/lanes.json`.
- README's adjacent-skill routing section points to `docs/lanes.json` and `references/lane_registry.md`.
- MCP docs, if present, state that `plan_public_records` and `draft_extraction` use registry lane/template names.
- Avoid duplicating the full lane table in more than one human-maintained document.

- [ ] **Step 1: Update docs**

Keep this task docs-only. If you discover missing MCP docs because Phase 4 is not landed, add a note in this plan's final report rather than inventing Phase 4 artifacts.

- [ ] **Step 2: Verify**

Run:

```bash
cd <project_root>/
rg -n "CLI `draft-extraction --template` supports|legal-court.*corporate.*education" docs README.md .agents/skills/truecrime-cult-research/SKILL.md
.venv/bin/python -m pytest tests/test_lanes_json.py tests/test_lanes_docs_generation.py tests/test_skill_docs_tool_access.py -v
```

The first `rg` should find no stale hand-maintained template list outside generated docs or tests.

- [ ] **Step 3: Commit**

```bash
git add docs README.md
git commit -m "docs(lanes): point public docs at canonical registry

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Final drift audit

**Files:**
- No new source files expected unless tests expose a gap.

**Checks:**

```bash
cd <project_root>/
.venv/bin/python -m compileall -q src .agents/skills/truecrime-cult-research/scripts
.venv/bin/python -m pytest -q
.venv/bin/python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction --help >/tmp/trcr-draft-help.txt
.venv/bin/python .agents/skills/truecrime-cult-research/scripts/tcr.py plan-public-records --help >/tmp/trcr-plan-help.txt
rg -n "\"(legal-court|corporate|education|licensing-professional|media-transcript|property-location|missing-persons|geographical-location|foia-open-records|source-capture|contradiction)\"" src/case_builder .agents/skills/truecrime-cult-research/scripts/tcr.py
```

Expected:

- `compileall` is silent.
- full suite green.
- CLI help commands succeed.
- The final `rg` should show registry reads/tests/docs only; any surviving hard-coded lane map in runtime code needs review.

- [ ] **Commit if final fixes were needed**

Stage only files changed by the final drift audit, then commit:

```bash
git commit -m "test(lanes): lock lane registry drift checks

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Self-Review Notes

- **Spec coverage:** Component 6 requires tool access docs, adjacent-skill op-name alignment, and `docs/lanes.json` as the single vocabulary source. Tasks 1-3 make the registry real and consumed by runtime code; Tasks 4-6 update generated skill references and public docs.
- **Safety posture:** Route suggestions remain lead-only; registry rows do not become evidence; gated import still requires explicit user approval; generated docs must not weaken privacy/redaction language.
- **Drift controls:** Tests compare template files, lane IDs, generated docs, skill mentions, and runtime compatibility exports against `docs/lanes.json`.
- **Intentional compromise:** Long domain-specific packet checklists in `topic_extraction_templates.md` remain human-authored. The generated `lane_registry.md` and routing matrix carry canonical lane metadata; narrative packet guidance remains editable but is tested against registry IDs.
