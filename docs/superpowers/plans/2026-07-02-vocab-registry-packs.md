# Vocabulary Externalization Implementation Plan (Stage 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the case-specific keyword vocabulary embedded in the analysis classifiers into registry-shipped default packs with per-case overrides, and replace silent classification defaults with an explicit `unclassified` bucket.

**Architecture:** Two new canonical shards in `docs/registry/analysis/` (vocabulary + scoring) are mirrored into the packaged `core.lanes.registry_data` (existing drift-test pattern). A loader in the analysis package parses them into a pydantic `VocabPacks` model and merges an optional per-case override file (`data/cases/<slug>/analysis_vocabulary.json`). Classifiers become generic pack-driven matchers taking a `packs` argument threaded through the existing `AnalysisContext`. Case-specific terms (`promis`, `inslaw`, `jonestown`, `narconon`, `monarch`, …) leave `src/` entirely and land in an example override pack in the synthetic case fixture; a governance test bans them from ever returning to `src/`.

**Tech Stack:** Python ≥3.10, pydantic (required dep from stage 1), stdlib json/importlib.resources, pytest.

**Spec:** `docs/superpowers/specs/2026-07-02-src-skills-stabilization-design.md` (Stage 2 section).

**Recorded decisions (carried from stage 1):**
- Extraction-packet/manifest pydantic models stay deferred — this stage touches classification vocabulary, not extraction templates; packet typing is its own follow-up after stage 2 (do not fold it in here).
- `CRK_CASES_ROOT`/`CRK_SKILL_ROOT` consolidation into `CrkSettings` is stage 3 material (CLI/MCP boundary work), not stage 2.
- Structural/safety classification rules stay in code, NOT in packs: `co_mentioned` relations always classify as `hypothesis_requires_more_sources` / family `lead_only_co_mentions`; `status == "disputed"` → `contested_overlap`; `status == "unverified"` or `"lead"` in text → `hypothesis_requires_more_sources`; `record_kind == "event_link"` → `personnel_bridge` (an event link is by definition an entity-event participation bridge); bridge-path structure rules (`lead`/`alleged` in notes, path length ≤ 2) stay in code. Only keyword→label term lists move to packs. This preserves the safety contract: co-mention and uncertainty handling cannot be weakened by a pack file.
- `unclassified` is a REPORT-TIME bucket only. It is never written to ledger records and is NOT added to the `relationship_class` enum in `docs/schemas/` (schemas are untouched, per the spec's non-goals).

## Global Constraints

- Branch: all work on `refactor/vocab-registry-packs`, cut from `dev`.
- Modules under 200 non-comment LOC; governed dirs max 4 direct files (README.md/`__init__.py` exempt under `src/`) and max 3 direct child dirs; every Python-bearing dir under `src/` keeps a README.md. CHECK the target directory's counts before creating any file (stage 1 tripped this three times).
- `docs/registry/` is canonical; `src/core/lanes/registry_data/` is its packaged mirror, kept byte-identical by `tests/quality/governance/platform/test_packaging_policy.py::test_packaged_registry_data_matches_canonical_docs_registry` (`REGISTRY_SHARDS` tuple).
- Do not change `docs/schemas/` or any safety-contract behavior (public gates, co-mention handling, uncertainty preservation).
- Test command form: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest <path> -q` — abbreviated `PYTEST <path>`.
- Commit after every task; commit messages end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Pydantic contract from stage 1: pack payloads are `BaseModel`s; no `BaseSettings` anywhere in this stage.

---

### Task 1: Registry shards for default vocabulary + packaged mirror

**Files:**
- Create: `docs/registry/analysis/vocabulary.json`
- Create: `docs/registry/analysis/scoring.json`
- Create: `src/core/lanes/registry_data/analysis/vocabulary.json` (copy)
- Create: `src/core/lanes/registry_data/analysis/scoring.json` (copy)
- Modify: `pyproject.toml` (`[tool.setuptools.package-data]` — add `"registry_data/analysis/*.json"` to the `"core.lanes"` list)
- Modify: `tests/quality/governance/platform/test_packaging_policy.py` (`REGISTRY_SHARDS` gains the two new entries)

**Interfaces:**
- Produces: the two shard files, resolvable both from checkout `docs/registry/analysis/` and packaged `files("core.lanes")/"registry_data"/"analysis"`. Later tasks rely on the exact key names below.

Shape check: `docs/registry/` gains a 3rd child dir (has `lanes`, `templates`) — at the limit, OK. `registry_data/` likewise. Verify with `PYTEST tests/quality/governance/test_repository_shape.py -q` after creating.

- [ ] **Step 1: Extend the drift test (failing first)**

In `test_packaging_policy.py`, extend `REGISTRY_SHARDS`:

```python
REGISTRY_SHARDS = (
    "index.json",
    "env_vars.json",
    "lanes.schema.json",
    "lanes/public_records_core.json",
    "lanes/public_records_media.json",
    "lanes/review.json",
    "lanes/support.json",
    "templates/extraction.json",
    "analysis/vocabulary.json",
    "analysis/scoring.json",
)
```

Run: `PYTEST tests/quality/governance/platform/test_packaging_policy.py::test_packaged_registry_data_matches_canonical_docs_registry -q`
Expected: FAIL with `FileNotFoundError` on `analysis/vocabulary.json`.

- [ ] **Step 2: Create `docs/registry/analysis/vocabulary.json`**

These are the NEUTRAL defaults — the generic subset of the term lists currently hardcoded in `src/adapters/ops/evidence/reports/analysis/relationships.py` and `paths.py`. Case-specific terms are deliberately absent (they move to the synthetic-case override in Task 5). Pack order matters: classifiers test packs top-to-bottom, first match wins.

```json
{
  "version": 1,
  "relation_families": [
    {"key": "treatment_lineage", "terms": ["found", "co_found", "member", "participant", "opened", "completed_treatment", "program"]},
    {"key": "legal_criminal_or_family", "terms": ["father", "family", "sentenced", "criminal", "teacher", "headmaster", "hired"]},
    {"key": "institutional_inquiry_context", "terms": ["institution", "contract", "inquiry"]},
    {"key": "category_bridges", "terms": ["behavior", "authority", "category", "context"]}
  ],
  "relationship_classes": [
    {"key": "documented_successor", "terms": ["successor", "part_of_program", "component_of", "absorbed_into", "outgrowth", "redesignated", "program_lineage"]},
    {"key": "method_diffusion", "terms": ["therapeutic_community_model", "therapeutic_community", "therapeutic-community", "source_model_context", "model_context", "reformulated_program_context", "reported_method", "treatment_context", "treatment-model", "treatment model", "treatment-method", "treatment method", "prior_treatment_context", "method", "behavior_modification", "behavior modification", "authority_conformity", "authority/conformity", "drug_rehabilitation", "drug rehabilitation", "rehabilitation program", "drug rehab category", "category_member_context", "category bridge", "category_bridge", "behavioral context", "peer pressure", "self-help", "residential program", "source_describes_as", "writings_described_as_basis", "origin_context_for"]},
    {"key": "narrative_inheritance", "terms": ["narrative", "legend", "appears_in_narrative", "alleged_spin_off"]},
    {"key": "contested_overlap", "terms": ["contested", "reported_allegation", "allegation", "unclear", "boundary", "further investigation"]},
    {"key": "personnel_bridge", "terms": ["co_founder", "founder", "member", "participant", "researcher", "affiliated", "classmate", "father", "teacher", "headmaster", "sentenced", "worked", "guided", "approved_project"]}
  ],
  "bridge_labels": [],
  "layer_order": {
    "person": 1,
    "institution": 2,
    "organization": 3,
    "group": 4,
    "event_series": 5,
    "event": 6,
    "object": 7,
    "publication": 8,
    "document": 9,
    "place_alias": 10,
    "entity": 11
  }
}
```

- [ ] **Step 3: Create `docs/registry/analysis/scoring.json`**

Values copied exactly from `src/adapters/ops/evidence/reports/analysis/classifiers.py` (`STATUS_SCORE`, `GRADE_SCORE`):

```json
{
  "version": 1,
  "status_scores": {
    "verified": 1.0,
    "corroborated": 0.9,
    "single_source": 0.65,
    "disputed": 0.35,
    "unverified": 0.2,
    "excluded_from_public_script": 0.1,
    "false_or_retracted": 0.05
  },
  "grade_scores": {"A": 1.0, "B": 0.82, "C": 0.55, "D": 0.25, "X": 0.0}
}
```

- [ ] **Step 4: Copy to the packaged mirror and register package data**

```bash
mkdir -p src/core/lanes/registry_data/analysis
cp docs/registry/analysis/vocabulary.json docs/registry/analysis/scoring.json src/core/lanes/registry_data/analysis/
```

In `pyproject.toml`:

```toml
"core.lanes" = [
  "registry_data/*.json",
  "registry_data/lanes/*.json",
  "registry_data/templates/*.json",
  "registry_data/analysis/*.json",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `PYTEST tests/quality/governance/platform/test_packaging_policy.py tests/quality/governance/test_repository_shape.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add docs/registry/analysis src/core/lanes/registry_data/analysis pyproject.toml tests/quality/governance/platform/test_packaging_policy.py
git commit -m "feat(registry): add default analysis vocabulary and scoring shards"
```

---

### Task 2: VocabPacks loader with per-case override merge

**Files:**
- Create: `src/adapters/ops/evidence/reports/analysis/vocabulary.py`
- Test: `tests/runtime/unit/ops/test_analysis_vocabulary.py` (dir currently has 3 counted files — becomes 4, at the limit; verify with the shape test)

**Interfaces:**
- Consumes: `core.lanes.registry.default_lanes_path()` (existing; returns checkout `docs/registry` Path or packaged Traversable), shards from Task 1.
- Produces (later tasks import these from `adapters.ops.evidence.reports.analysis.vocabulary`):
  - `class TermPack(BaseModel)`: `key: str`, `terms: list[str]`
  - `class VocabPacks(BaseModel)`: `version: int = 1`, `relation_families: list[TermPack]`, `relationship_classes: list[TermPack]`, `bridge_labels: list[TermPack]`, `layer_order: dict[str, int]`, `status_scores: dict[str, float]`, `grade_scores: dict[str, float]`
  - `load_default_packs() -> VocabPacks` (cached)
  - `load_case_packs(case_dir: str | Path) -> VocabPacks` (defaults merged with `<case_dir>/analysis_vocabulary.json` when present; missing file → defaults; malformed file → `CasefileError` naming the file)
  - `match_pack(text: str, packs: list[TermPack]) -> str | None` (first pack whose any term is a substring of `text`, top-to-bottom; returns its `key`)
  - `CASE_PACK_FILENAME = "analysis_vocabulary.json"`

Merge semantics (implement exactly): for the three pack lists, an override entry whose `key` matches an existing pack EXTENDS that pack's terms (appended, deduplicated, original order kept); an override entry with a new `key` is INSERTED BEFORE the defaults (case-specific packs are more specific, so they win the top-to-bottom scan). For `layer_order`/`status_scores`/`grade_scores`, override keys replace per-key (dict merge, override wins). An override file may supply any subset of the six top-level keys.

- [ ] **Step 1: Write the failing tests**

Create `tests/runtime/unit/ops/test_analysis_vocabulary.py`:

```python
"""Vocabulary pack loading, matching, and per-case override merging."""

from __future__ import annotations

import json

import pytest

from adapters.ops.evidence.reports.analysis.vocabulary import (
    CASE_PACK_FILENAME,
    TermPack,
    load_case_packs,
    load_default_packs,
    match_pack,
)
from core.casefile import CasefileError


def test_default_packs_load_from_registry():
    packs = load_default_packs()
    class_keys = [pack.key for pack in packs.relationship_classes]
    assert class_keys[0] == "documented_successor"
    assert "personnel_bridge" in class_keys
    assert packs.layer_order["person"] == 1
    assert packs.status_scores["verified"] == 1.0
    assert packs.grade_scores["X"] == 0.0


def test_defaults_contain_no_case_specific_terms():
    packs = load_default_packs()
    all_terms = " ".join(t for p in packs.relationship_classes + packs.relation_families + packs.bridge_labels for t in p.terms)
    for banned in ("promis", "inslaw", "jonestown", "narconon", "monarch", "montauk", "hubbard", "finders"):
        assert banned not in all_terms


def test_match_pack_first_match_wins():
    packs = [TermPack(key="a", terms=["alpha"]), TermPack(key="b", terms=["alpha", "beta"])]
    assert match_pack("has alpha inside", packs) == "a"
    assert match_pack("only beta here", packs) == "b"
    assert match_pack("nothing", packs) is None


def test_case_override_extends_and_prepends(tmp_path):
    (tmp_path / "case.json").write_text(json.dumps({"case_id": "t"}), encoding="utf-8")
    override = {
        "relationship_classes": [
            {"key": "contested_overlap", "terms": ["housecat_inquiry"]},
            {"key": "software_inquiry_context", "terms": ["promiscase"]},
        ],
        "layer_order": {"person": 99},
    }
    (tmp_path / CASE_PACK_FILENAME).write_text(json.dumps(override), encoding="utf-8")
    packs = load_case_packs(tmp_path)
    keys = [p.key for p in packs.relationship_classes]
    assert keys[0] == "software_inquiry_context"          # new key prepended
    contested = next(p for p in packs.relationship_classes if p.key == "contested_overlap")
    assert "housecat_inquiry" in contested.terms          # existing key extended
    assert "contested" in contested.terms                 # defaults kept
    assert packs.layer_order["person"] == 99              # dict-merge override
    assert packs.layer_order["institution"] == 2          # untouched default
    assert load_default_packs().layer_order["person"] == 1  # defaults not mutated


def test_missing_override_returns_defaults(tmp_path):
    (tmp_path / "case.json").write_text(json.dumps({"case_id": "t"}), encoding="utf-8")
    assert load_case_packs(tmp_path).layer_order["person"] == 1


def test_malformed_override_fails_fast(tmp_path):
    (tmp_path / "case.json").write_text(json.dumps({"case_id": "t"}), encoding="utf-8")
    (tmp_path / CASE_PACK_FILENAME).write_text("{not json", encoding="utf-8")
    with pytest.raises(CasefileError) as excinfo:
        load_case_packs(tmp_path)
    assert CASE_PACK_FILENAME in str(excinfo.value)
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTEST tests/runtime/unit/ops/test_analysis_vocabulary.py -q`
Expected: FAIL with `ModuleNotFoundError: ...vocabulary`.

- [ ] **Step 3: Implement the loader**

Create `src/adapters/ops/evidence/reports/analysis/vocabulary.py`:

```python
"""Pack-driven vocabulary for analysis classification, registry-backed with per-case overrides."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from core.casefile import CasefileError, case_path
from core.lanes.registry import default_lanes_path

CASE_PACK_FILENAME = "analysis_vocabulary.json"


class TermPack(BaseModel):
    key: str
    terms: list[str]


class VocabPacks(BaseModel):
    version: int = 1
    relation_families: list[TermPack] = Field(default_factory=list)
    relationship_classes: list[TermPack] = Field(default_factory=list)
    bridge_labels: list[TermPack] = Field(default_factory=list)
    layer_order: dict[str, int] = Field(default_factory=dict)
    status_scores: dict[str, float] = Field(default_factory=dict)
    grade_scores: dict[str, float] = Field(default_factory=dict)


def match_pack(text: str, packs: list[TermPack]) -> str | None:
    for pack in packs:
        if any(term in text for term in pack.terms):
            return pack.key
    return None


def _read_registry_json(name: str) -> dict:
    root = default_lanes_path()
    node = root / "analysis" / name if isinstance(root, Path) else root.joinpath("analysis").joinpath(name)
    return json.loads(node.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _default_packs() -> VocabPacks:
    payload = {**_read_registry_json("vocabulary.json"), **_read_registry_json("scoring.json")}
    return VocabPacks.model_validate(payload)


def load_default_packs() -> VocabPacks:
    return _default_packs().model_copy(deep=True)


def _merge_packs(base: list[TermPack], overrides: list[TermPack]) -> list[TermPack]:
    merged = {pack.key: pack for pack in base}
    prepended: list[TermPack] = []
    for override in overrides:
        if override.key in merged:
            existing = merged[override.key]
            seen = set(existing.terms)
            existing.terms.extend(term for term in override.terms if term not in seen)
        else:
            prepended.append(override)
    return [*prepended, *(merged[pack.key] for pack in base)]


def load_case_packs(case_dir: str | Path) -> VocabPacks:
    packs = load_default_packs()
    override_path = case_path(case_dir) / CASE_PACK_FILENAME
    if not override_path.exists():
        return packs
    try:
        raw = json.loads(override_path.read_text(encoding="utf-8"))
        override = VocabPacks.model_validate(raw)
    except Exception as exc:
        raise CasefileError(f"Malformed {CASE_PACK_FILENAME} in {case_path(case_dir)}: {exc}") from exc
    packs.relation_families = _merge_packs(packs.relation_families, override.relation_families)
    packs.relationship_classes = _merge_packs(packs.relationship_classes, override.relationship_classes)
    packs.bridge_labels = _merge_packs(packs.bridge_labels, override.bridge_labels)
    packs.layer_order.update(override.layer_order)
    packs.status_scores.update(override.status_scores)
    packs.grade_scores.update(override.grade_scores)
    return packs
```

Note: `load_default_packs` returns a deep copy so callers (and the merge) can never mutate the cached instance — `test_case_override_extends_and_prepends` asserts this.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTEST tests/runtime/unit/ops/test_analysis_vocabulary.py tests/quality/governance/test_repository_shape.py -q`
Expected: PASS. (Shape: `analysis/` gains a 4th counted file — at the limit.)

- [ ] **Step 5: Commit**

```bash
git add src/adapters/ops/evidence/reports/analysis/vocabulary.py tests/runtime/unit/ops/test_analysis_vocabulary.py
git commit -m "feat(analysis): add registry-backed vocabulary pack loader"
```

---

### Task 3: Pack-driven relationship classifiers with explicit unclassified

**Files:**
- Modify: `src/adapters/ops/evidence/reports/analysis/relationships.py` (full rewrite of both functions)
- Modify: `src/adapters/ops/evidence/reports/common.py:26-33` (`RELATIONSHIP_CLASS_TITLES` gains `unclassified`)
- Test: `tests/runtime/unit/ops/test_analysis_vocabulary.py` (extend — same file, keeps dir at 4)

**Interfaces:**
- Consumes: `VocabPacks`, `load_default_packs`, `match_pack` from Task 2.
- Produces: `relation_family(relation_type: str, record_kind: str = "relationship", packs: VocabPacks | None = None) -> str` and `relationship_class(record: dict[str, Any], record_kind: str = "relationship", packs: VocabPacks | None = None) -> str`. `packs=None` means `load_default_packs()`. Both return `"unclassified"` when no structural rule or pack matches. Existing positional call sites (`relationship_class(rel)`, `relationship_class(link, "event_link")`) keep working unchanged.

- [ ] **Step 1: Write the failing tests (append to the Task 2 test file)**

```python
from adapters.ops.evidence.reports.analysis.relationships import relation_family, relationship_class
from adapters.ops.evidence.reports.analysis.vocabulary import VocabPacks


def test_relationship_class_unmatched_falls_to_unclassified():
    record = {"rel_id": "r1", "relation_type": "vague_link", "status": "corroborated", "notes": ""}
    assert relationship_class(record) == "unclassified"


def test_relationship_class_structural_rules_survive_empty_packs():
    empty = VocabPacks()
    assert relationship_class({"relation_type": "co_mentioned_with"}, packs=empty) == "hypothesis_requires_more_sources"
    assert relationship_class({"relation_type": "x", "status": "disputed"}, packs=empty) == "contested_overlap"
    assert relationship_class({"relation_type": "x", "status": "unverified"}, packs=empty) == "hypothesis_requires_more_sources"
    assert relationship_class({"relation_type": "x"}, "event_link", packs=empty) == "personnel_bridge"


def test_relationship_class_respects_explicit_field():
    assert relationship_class({"relationship_class": "method_diffusion", "relation_type": "x"}) == "method_diffusion"


def test_relation_family_pack_driven_and_unclassified():
    assert relation_family("completed_treatment_at") == "treatment_lineage"
    assert relation_family("co_mentioned_with") == "lead_only_co_mentions"
    assert relation_family("x", "event_link") == "event_context"
    assert relation_family("totally_novel_relation") == "unclassified"


def test_case_pack_changes_classification(tmp_path):
    import json as _json
    (tmp_path / "case.json").write_text(_json.dumps({"case_id": "t"}), encoding="utf-8")
    (tmp_path / "analysis_vocabulary.json").write_text(
        _json.dumps({"relationship_classes": [{"key": "contested_overlap", "terms": ["zzz_special_inquiry"]}]}),
        encoding="utf-8",
    )
    from adapters.ops.evidence.reports.analysis.vocabulary import load_case_packs

    record = {"rel_id": "r1", "relation_type": "x", "notes": "zzz_special_inquiry raised", "status": "corroborated"}
    assert relationship_class(record) == "unclassified"
    assert relationship_class(record, packs=load_case_packs(tmp_path)) == "contested_overlap"
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTEST tests/runtime/unit/ops/test_analysis_vocabulary.py -q`
Expected: new tests FAIL (`unexpected keyword argument 'packs'` / wrong return values from the hardcoded lists).

- [ ] **Step 3: Rewrite `relationships.py`**

```python
"""Relationship-family and class classifiers, driven by vocabulary packs."""

from __future__ import annotations

from typing import Any

from adapters.ops.evidence.reports.analysis.vocabulary import VocabPacks, load_default_packs, match_pack
from adapters.ops.evidence.reports.common import RELATIONSHIP_CLASS_TITLES


def relation_family(relation_type: str, record_kind: str = "relationship", packs: VocabPacks | None = None) -> str:
    rel = relation_type.lower()
    if "co_mentioned" in rel:
        return "lead_only_co_mentions"
    if record_kind == "event_link":
        return "event_context"
    active = packs or load_default_packs()
    return match_pack(rel, active.relation_families) or "unclassified"


def relationship_class(record: dict[str, Any], record_kind: str = "relationship", packs: VocabPacks | None = None) -> str:
    explicit = str(record.get("relationship_class") or "").strip()
    if explicit in RELATIONSHIP_CLASS_TITLES:
        return explicit
    relation_type = str(record.get("relation_type", "")).lower()
    status = str(record.get("status", "")).lower()
    text = " ".join(
        str(record.get(field) or "").lower()
        for field in ("rel_id", "event_link_id", "claim_id", "relation_type", "status", "notes", "basis", "summary")
    )
    if "co_mentioned" in relation_type:
        return "hypothesis_requires_more_sources"
    active = packs or load_default_packs()
    matched = match_pack(text, active.relationship_classes)
    if matched in {"documented_successor", "method_diffusion", "narrative_inheritance"}:
        return matched
    if status == "disputed" or matched == "contested_overlap":
        return "contested_overlap"
    if status == "unverified" or "lead" in text:
        return "hypothesis_requires_more_sources"
    if record_kind == "event_link" or matched == "personnel_bridge":
        return "personnel_bridge"
    return matched or "unclassified"
```

Ordering note (this preserves the original rule precedence): term packs for successor/method/narrative fire before status rules, exactly as the old code checked those lists first; the disputed-status rule ranks with `contested_overlap` terms; unverified/lead ranks above personnel terms; the bare fallthrough becomes `unclassified` instead of `personnel_bridge`. `match_pack` scans top-to-bottom so a case override prepending a new pack key returns that key — which then reaches the final `return matched or "unclassified"` and surfaces as its own class (custom keys must also be titled; see the `common.py` note below).

In `common.py`, extend the titles map:

```python
RELATIONSHIP_CLASS_TITLES = {
    "documented_successor": "Documented succession / component lineage",
    "method_diffusion": "Method diffusion / institutional borrowing",
    "personnel_bridge": "Personnel / role / affiliation bridge",
    "narrative_inheritance": "Narrative inheritance / story-world growth",
    "contested_overlap": "Contested overlap / disputed institutional tie",
    "hypothesis_requires_more_sources": "Hypothesis requiring more sources",
    "unclassified": "Unclassified (no pack or rule matched)",
}
```

Check `common.py`'s consumers of the titles map render unknown keys gracefully: `grep -n "RELATIONSHIP_CLASS_TITLES" -r src/ | grep -v common.py` and confirm each use is `.get(key, key)`-style or a membership test — if any indexes directly (`TITLES[key]`), change it to `.get(key, key)` so custom override-pack classes don't KeyError. List what you found in the report.

- [ ] **Step 4: Run tests**

Run: `PYTEST tests/runtime/unit/ops/test_analysis_vocabulary.py -q`
Expected: PASS.

- [ ] **Step 5: Run the broader suite to catch behavior shifts**

Run: `PYTEST tests/runtime -q`
Expected: PASS. If an existing test asserted the old silent `personnel_bridge`/`institutional_or_career_roles` fallbacks, update that assertion to `unclassified` and flag it in your report (that changed behavior is the point of this task); any OTHER failure is a regression — fix or report BLOCKED.

- [ ] **Step 6: Commit**

```bash
git add src/adapters/ops/evidence/reports/analysis/relationships.py src/adapters/ops/evidence/reports/common.py tests/runtime/unit/ops/test_analysis_vocabulary.py
git commit -m "feat(analysis): pack-driven relationship classifiers with explicit unclassified"
```

---

### Task 4: Thread packs through paths, scoring, layers, and the analysis context

**Files:**
- Modify: `src/adapters/ops/evidence/reports/analysis/paths.py` (`analysis_graph` edge build ~line 86, `classify_bridge_path` ~line 139)
- Modify: `src/adapters/ops/evidence/reports/analysis/classifiers.py` (scores from packs)
- Modify: `src/adapters/ops/evidence/reports/analysis/command/builders/layered/vocab.py` (constant → pack lookup)
- Modify: `src/adapters/ops/evidence/reports/analysis/command/context.py` (`AnalysisContext.packs`)
- Modify: call sites listed in Step 2 (bridges.py, facets/boundary.py, builders/paths.py, layered builders)
- Test: extend `tests/runtime/unit/ops/test_analysis_vocabulary.py` + integration run

**Interfaces:**
- Consumes: `VocabPacks`, `load_case_packs` (Task 2); classifier signatures (Task 3).
- Produces:
  - `AnalysisContext` gains field `packs: VocabPacks`; `load_analysis_context` loads `packs = load_case_packs(cdir)` BEFORE building the graph and passes it down.
  - `analysis_graph(..., packs: VocabPacks | None = None)` — threads to the edge-dict `relationship_class(record, edge_type, packs=packs)`.
  - `classify_bridge_path(steps, meta, packs: VocabPacks | None = None) -> str` — its two label term lists come from `packs.bridge_labels` (`match_pack(labels, active.bridge_labels)` mapped to the bridge class named by the pack key); structure rules (bridge-class escalation by member classes, `lead`/`alleged` notes, path length) stay in code.
  - `classifiers.py`: `STATUS_SCORE`/`GRADE_SCORE` constants deleted; `status_score(status: str, packs: VocabPacks | None = None) -> float` and `source_grade_score(source_rows, packs: VocabPacks | None = None) -> float` read `packs.status_scores`/`packs.grade_scores` (default `load_default_packs()`); unknown grade fallback stays `0.35`.
  - `layered/vocab.py`: `LAYER_ORDER_MAP` constant deleted; `layer_order_map(packs: VocabPacks | None = None) -> dict[str, int]` returns `(packs or load_default_packs()).layer_order`.

- [ ] **Step 1: Write the failing tests (append to the same test file — watch its LOC; if it approaches 200 non-comment lines, split is NOT allowed by shape (dir at 4 files) so trim helper duplication instead)**

```python
def test_status_and_grade_scores_come_from_packs():
    from adapters.ops.evidence.reports.analysis.classifiers import source_grade_score, status_score

    assert status_score("verified") == 1.0
    custom = VocabPacks(status_scores={"verified": 0.5}, grade_scores={"A": 0.1})
    assert status_score("verified", packs=custom) == 0.5
    assert source_grade_score([{"reliability_grade": "A"}], packs=custom) == 0.1


def test_layer_order_map_reads_packs():
    from adapters.ops.evidence.reports.analysis.command.builders.layered.vocab import layer_order_map

    assert layer_order_map()["person"] == 1
    assert layer_order_map(VocabPacks(layer_order={"person": 42}))["person"] == 42


def test_classify_bridge_path_label_terms_from_packs():
    from adapters.ops.evidence.reports.analysis.paths import classify_bridge_path

    steps = [("a", "b", {"relation_type": "x", "status": "corroborated", "edge_type": "relationship"})]
    meta = {"a": {"label": "zeta widget hub"}, "b": {"label": "other"}}
    default = classify_bridge_path(steps, meta)
    assert default in {"direct_or_near_direct", "indirect_context_bridge", "unclassified_bridge"} or default.endswith("_bridge")
    custom = VocabPacks(bridge_labels=[TermPack(key="category_bridge", terms=["zeta widget hub"])])
    assert classify_bridge_path(steps, meta, packs=custom) == "category_bridge"
```

Run: `PYTEST tests/runtime/unit/ops/test_analysis_vocabulary.py -q` — Expected: FAIL (missing kwargs/functions).

- [ ] **Step 2: Implement the threading**

`classifiers.py` — replace the two constants and the grade function:

```python
from adapters.ops.evidence.reports.analysis.vocabulary import VocabPacks, load_default_packs


def status_score(status: str, packs: VocabPacks | None = None) -> float:
    return (packs or load_default_packs()).status_scores.get(status, 0.0)


def source_grade_score(source_rows: list[dict[str, Any]], packs: VocabPacks | None = None) -> float:
    if not source_rows:
        return 0.0
    grades = (packs or load_default_packs()).grade_scores
    return round(max(grades.get(str(source.get("reliability_grade", "")), 0.35) for source in source_rows), 3)
```

First check existing consumers: `grep -rn "STATUS_SCORE\|GRADE_SCORE\|status_score\|source_grade_score" src/ tests/ --include='*.py'` — convert every direct `STATUS_SCORE[...]`/`.get(...)` dict access to `status_score(status, packs=...)` calls, threading `ctx.packs` where a ctx is in scope and defaults elsewhere. List every converted site in your report.

`layered/vocab.py`:

```python
"""Shared layered graph vocabulary, pack-backed."""

from __future__ import annotations

from adapters.ops.evidence.reports.analysis.vocabulary import VocabPacks, load_default_packs


def layer_order_map(packs: VocabPacks | None = None) -> dict[str, int]:
    return dict((packs or load_default_packs()).layer_order)
```

Convert `LAYER_ORDER_MAP` consumers (`grep -rn "LAYER_ORDER_MAP" src/ --include='*.py'`) to `layer_order_map(ctx.packs)` where ctx is in scope, else `layer_order_map()`.

`paths.py`: give `analysis_graph` and `classify_bridge_path` a trailing `packs: VocabPacks | None = None` parameter. In the edge dict (~line 86): `"relationship_class": relationship_class(record, edge_type, packs=packs)`. In `classify_bridge_path`, replace the two hardcoded label lists:

```python
    active = packs or load_default_packs()
    label_match = match_pack(labels, active.bridge_labels)
    if label_match:
        return label_match
```

placed exactly where the two `any(term in labels ...)` checks were (after the class-escalation checks, before the `lead`/`alleged` notes check). The pack key IS the returned bridge class, so override packs can add `institutional_software_bridge` etc. Also thread packs into the internal `relationship_class(step[2], ..., packs=packs)` call at ~line 142.

`command/context.py`: add to the dataclass `packs: VocabPacks` (import `VocabPacks`, `load_case_packs` from the vocabulary module) and in `load_analysis_context`, immediately after `cdir` is resolved: `packs = load_case_packs(cdir)`; pass `packs=packs` into the `analysis_graph(...)` call and include `packs=packs` in the `AnalysisContext(...)` construction.

Call sites (from `grep -rn "relationship_class(\|classify_bridge_path(\|relation_family(" src/ --include='*.py'`), each gains `packs=ctx.packs`:
- `command/builders/bridges.py` — 6 sites (lines ~53, 65, 123, 129, 135, 145)
- `command/builders/facets/boundary.py` — 3 sites (lines ~44, 57, 89)
- `command/builders/paths.py` — its `classify_bridge_path` usage
Re-run the grep after editing; any remaining call without `packs=` must be one with no ctx in scope (defaults are then correct) — justify each in the report.

- [ ] **Step 3: Run unit + full runtime suites**

Run: `PYTEST tests/runtime/unit/ops/test_analysis_vocabulary.py -q` then `PYTEST tests/runtime -q`
Expected: PASS (same caveat as Task 3 Step 5 for tests pinning old constants).

- [ ] **Step 4: Integration sanity — analysis export against the synthetic case**

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- crk-ledger export-analysis-charts data/examples/synthetic_case 2>&1 | tail -3
```

Expected: completes without error (check the command name with `crk-ledger --help` if it differs; the op is `export_analysis_charts`). Generated exports land in the fixture's gitignored/working area — do NOT commit changed export artifacts; `git status --short` must show only your source/test changes.

- [ ] **Step 5: Commit**

```bash
git add src/adapters/ops/evidence/reports/analysis tests/runtime/unit/ops/test_analysis_vocabulary.py
git commit -m "feat(analysis): thread vocabulary packs through paths, scoring, and layers"
```

---

### Task 5: Example per-case override pack + format documentation

**Files:**
- Create: `data/examples/synthetic_case/analysis_vocabulary.json`
- Modify: `docs/registry/README.md` (document the shards + override format)
- Test: `tests/runtime/integration/operations/validation/test_validate_schemas.py` dir is at 1 file — add `tests/runtime/integration/operations/validation/test_case_vocab_override.py`

**Interfaces:**
- Consumes: loader + classifiers from Tasks 2-4.
- Produces: the documented override-pack example carrying every case-specific term removed from `src/`.

- [ ] **Step 1: Create the example override pack**

`data/examples/synthetic_case/analysis_vocabulary.json` — this is where the case-specific vocabulary lives now. (`data/examples/` is tracked; `data/cases/` is the gitignored working area.)

```json
{
  "version": 1,
  "relation_families": [
    {"key": "software_inquiry_context", "terms": ["promis", "inslaw", "cia"]}
  ],
  "relationship_classes": [
    {"key": "method_diffusion", "terms": ["based on hubbard", "narconon", "drug residues", "obedience research", "classic studies in the conformity debate"]},
    {"key": "narrative_inheritance", "terms": ["monarch", "montauk", "milab", "super_soldier", "targeted_individual", "synthetic_telepathy"]},
    {"key": "contested_overlap", "terms": ["house_inquiry", "house question", "question/inquiry", "inquiry lane", "promis", "inslaw", "finders", "jonestown"]}
  ],
  "bridge_labels": [
    {"key": "institutional_software_bridge", "terms": ["promis", "inslaw", "central intelligence agency", "cia"]},
    {"key": "category_bridge", "terms": ["drug rehabilitation program context", "behavioral-control and authority context"]}
  ]
}
```

- [ ] **Step 2: Document the format in `docs/registry/README.md`**

Append a section (adapt heading level to the file's existing structure):

```markdown
## Analysis vocabulary packs

`analysis/vocabulary.json` and `analysis/scoring.json` hold the neutral default
classification vocabulary for analysis reports: ordered term packs for relation
families, relationship classes, and bridge labels, plus layer ordering and
status/grade score tables. Classifiers scan packs top-to-bottom; first match wins;
records matching no pack surface as `unclassified` rather than inheriting an
implied label.

A case may extend the defaults with `analysis_vocabulary.json` in its case
directory (`data/cases/<slug>/`). Override entries with an existing `key` extend
that pack's terms; entries with a new `key` are inserted before the defaults
(more specific wins). `layer_order`/`status_scores`/`grade_scores` merge per key.
Case-specific investigation vocabulary belongs in the case override, never in
these defaults — see `data/examples/synthetic_case/analysis_vocabulary.json`
for a worked example.
```

- [ ] **Step 3: Write the integration test**

`tests/runtime/integration/operations/validation/test_case_vocab_override.py`:

```python
"""The synthetic case's override pack changes classification end to end."""

from __future__ import annotations

from pathlib import Path

from adapters.ops.evidence.reports.analysis.relationships import relationship_class
from adapters.ops.evidence.reports.analysis.vocabulary import load_case_packs, load_default_packs

SYNTHETIC_CASE = Path(__file__).resolve().parents[5] / "data" / "examples" / "synthetic_case"


def test_synthetic_override_loads_and_prepends_case_packs():
    packs = load_case_packs(SYNTHETIC_CASE)
    family_keys = [p.key for p in packs.relation_families]
    assert family_keys[0] == "software_inquiry_context"
    assert "software_inquiry_context" not in [p.key for p in load_default_packs().relation_families]


def test_case_specific_term_classifies_only_with_override():
    record = {"rel_id": "r1", "relation_type": "linked_via_narconon_program_history", "status": "corroborated", "notes": "narconon"}
    assert relationship_class(record) == "unclassified"
    assert relationship_class(record, packs=load_case_packs(SYNTHETIC_CASE)) == "method_diffusion"
```

- [ ] **Step 4: Run tests**

Run: `PYTEST tests/runtime/integration/operations/validation/test_case_vocab_override.py tests/quality/governance/test_repository_shape.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add data/examples/synthetic_case/analysis_vocabulary.json docs/registry/README.md tests/runtime/integration/operations/validation/test_case_vocab_override.py
git commit -m "feat(examples): ship case-specific vocabulary as a per-case override pack"
```

---

### Task 6: Governance — ban case-specific vocabulary from src/ and validate pack shards

**Files:**
- Modify: `tests/quality/governance/test_data_safety.py` (case-term ban — check the file's current contents first; it is the intent-correct home for "no case residue in code")
- Modify: `tests/quality/governance/policy/test_lanes_json.py` (pack shard structure validation — registry-JSON policy home; dir is at 4 files, no new file allowed)

**Interfaces:** consumes shard files (Task 1) and `RELATIONSHIP_CLASS_TITLES` (Task 3).

- [ ] **Step 1: Add the case-term ban test**

In `test_data_safety.py` (match its existing imports/helpers — it likely has `KIT_ROOT` via `tests.helpers`):

```python
CASE_SPECIFIC_TERMS = (
    "promis", "inslaw", "jonestown", "narconon", "finders",
    "monarch", "montauk", "milab", "hubbard", "synanon",
)


def test_src_carries_no_case_specific_vocabulary():
    violations = []
    for path in (KIT_ROOT / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for term in CASE_SPECIFIC_TERMS:
            if term in text:
                violations.append(f"{path.relative_to(KIT_ROOT)}: {term}")
    assert violations == [], f"Case-specific vocabulary belongs in per-case override packs: {violations}"
```

Caution: `"promis"` is a substring of "promise"/"compromise" — run the test BEFORE the classifier rewrite is assumed clean and inspect any hits. If legitimate English words trip a term, tighten that term (e.g. use `"promis "` and `"promis\""` word-boundary variants or a regex `\bpromis\b`) rather than dropping it; show the final matcher in your report. Also verify the registry default shards stay clean: extend the same test to scan `docs/registry/analysis/*.json`.

- [ ] **Step 2: Add pack-shard structure validation to `test_lanes_json.py`**

```python
def test_analysis_vocabulary_shard_is_well_formed():
    payload = json.loads((KIT_ROOT / "docs" / "registry" / "analysis" / "vocabulary.json").read_text(encoding="utf-8"))
    known_classes = {
        "documented_successor", "method_diffusion", "personnel_bridge",
        "narrative_inheritance", "contested_overlap", "hypothesis_requires_more_sources",
    }
    for section in ("relation_families", "relationship_classes", "bridge_labels"):
        for pack in payload[section]:
            assert isinstance(pack["key"], str) and pack["key"]
            assert pack["terms"] and all(isinstance(t, str) and t for t in pack["terms"])
    assert {p["key"] for p in payload["relationship_classes"]} <= known_classes
    assert set(payload["layer_order"]) >= {"person", "institution", "event"}


def test_analysis_scoring_shard_is_well_formed():
    payload = json.loads((KIT_ROOT / "docs" / "registry" / "analysis" / "scoring.json").read_text(encoding="utf-8"))
    assert set(payload["status_scores"]) >= {"verified", "corroborated", "disputed", "unverified"}
    assert set(payload["grade_scores"]) == {"A", "B", "C", "D", "X"}
    for table in (payload["status_scores"], payload["grade_scores"]):
        assert all(0.0 <= v <= 1.0 for v in table.values())
```

Match the file's existing import style (`json`, `KIT_ROOT`). Mind the 200 non-comment LOC ceiling on the file; if it would exceed, report BLOCKED with the counts instead of restructuring.

- [ ] **Step 3: Run the governance lane**

Run: `PYTEST tests/quality/governance -q`
Expected: PASS — in particular the new ban test passes only because Tasks 3-5 removed the terms from `src/`.

- [ ] **Step 4: Commit**

```bash
git add tests/quality/governance/test_data_safety.py tests/quality/governance/policy/test_lanes_json.py
git commit -m "test(governance): ban case vocabulary from src and validate analysis shards"
```

---

### Task 7: Docs, changelog, and full verification

**Files:**
- Modify: `CHANGELOG.md` (`## [Unreleased]`)
- Modify: `src/adapters/ops/evidence/reports/analysis/README.md` (mention pack-driven classification — check current text first)

- [ ] **Step 1: CHANGELOG under `## [Unreleased]`**

```markdown
### Changed
- Analysis relationship/family/bridge classification is now driven by vocabulary packs from `docs/registry/analysis/`; records matching no pack or structural rule surface as `unclassified` instead of silently defaulting to `personnel_bridge`.
- Status/grade score tables and layer ordering moved from code constants to the `analysis/scoring.json` and `analysis/vocabulary.json` registry shards.

### Added
- Per-case vocabulary overrides: `data/cases/<slug>/analysis_vocabulary.json` extends or prepends the default packs (worked example in `data/examples/synthetic_case/`).
- Governance tests banning case-specific vocabulary from `src/` and validating the new registry shards.
```

If stage 1's `## [Unreleased]` entries are still unreleased, merge these into the same section (Keep a Changelog: one Unreleased block).

- [ ] **Step 2: Update the analysis README** — one short paragraph noting classifiers are pack-driven (`vocabulary.py`, registry shards, per-case override file) and that `unclassified` is a report-only bucket.

- [ ] **Step 3: Full verification**

```bash
moon run crk:check
moon run crk:test
uv run --cache-dir .uv-cache --no-project --with-editable . -- crk-ledger validate data/examples/synthetic_case
```

Expected: all green.

- [ ] **Step 4: Commit, then finish the branch**

```bash
git add CHANGELOG.md src/adapters/ops/evidence/reports/analysis/README.md
git commit -m "docs: record vocabulary externalization changes"
```

Use superpowers:finishing-a-development-branch to integrate back to `dev`. Do not push tags.
