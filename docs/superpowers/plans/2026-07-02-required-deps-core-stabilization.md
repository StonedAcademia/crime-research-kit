# Required Deps + Core Stabilization Implementation Plan (Stage 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Relax the zero-dependency contract to a pinned six-package required set and use it to stabilize the core: real `jsonschema` validation against packaged schemas, pydantic `BaseModel` classes for all ledger record types and `OpResult`, and `BaseSettings` env handling confined to process boundaries.

**Architecture:** `docs/schemas/` stays the canonical on-disk contract; the schema JSONs are mirrored as package data under `core.models` (same pattern as `core.lanes.registry_data`) and resolved via `importlib.resources`. Pydantic models in `core/models/records/` mirror the schemas and a governance drift test keeps them aligned. `core/config.py` becomes the single env reader (`CrkSettings`); deep modules fall back to constants and boundaries pass resolved values inward.

**Tech Stack:** Python ≥3.10, setuptools, pytest, jsonschema ≥4.20, pydantic ≥2.7, pydantic-settings ≥2.2, httpx, typer, jinja2 (last three added now per the dependency-policy decision; first used in stages 3-4).

**Spec:** `docs/superpowers/specs/2026-07-02-src-skills-stabilization-design.md` (Stage 1 section).

**Deferred from stage 1 (per the spec's "opportunistically, not exhaustively" clause):** extraction-packet and manifest models. Packet shape is template-driven — `fresh_default_extraction()` builds packets from `docs/registry/templates/extraction.json` registry data — so a static `BaseModel` would fight the template system. Packets get typed when stage 2 restructures registry-driven vocabulary (same data source), or when a stable packet envelope is extracted; record that decision in the stage 2 plan.

## Global Constraints

- Branch: all work on `refactor/required-deps-core`, cut from `dev`.
- Every module in `src/` stays under 200 non-comment LOC; governed dirs have 1-4 direct files and 0-3 direct child dirs; every Python-bearing directory keeps a `README.md` (`tests/quality/governance/test_repository_shape.py` enforces all three).
- Required deps are exactly: `jsonschema>=4.20.0`, `pydantic>=2.7`, `pydantic-settings>=2.2`, `httpx>=0.27`, `typer>=0.12`, `jinja2>=3.1`. No others.
- `BaseSettings` is instantiated only at process boundaries (`src/cli.py`, MCP server context). Nothing under `core/`, `pipeline/`, or `adapters/ops/` calls `CrkSettings()`.
- Preserve every `CRK_*` env var name and default value exactly as today.
- Do not change record schema files in `docs/schemas/` or safety-contract behavior.
- Test command form (from repo root): `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest <path> -q`. Abbreviated below as `PYTEST <path>`.
- Commit after every task; end commit messages with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Branch + required dependencies + packaging policy test

**Files:**
- Modify: `pyproject.toml` (project.dependencies, dev extra)
- Modify: `tests/quality/governance/platform/test_packaging_policy.py:18-35,62-67`

**Interfaces:**
- Produces: `pyproject.toml` `[project] dependencies` with the six pinned requirements; all later tasks may import jsonschema/pydantic/pydantic_settings unconditionally.

- [ ] **Step 1: Create the branch**

```bash
git status --short --branch   # expect clean, on dev
git checkout -b refactor/required-deps-core
```

- [ ] **Step 2: Update the packaging policy test (failing first)**

In `tests/quality/governance/platform/test_packaging_policy.py`, add below `EXPECTED_EXTRAS`:

```python
EXPECTED_REQUIRED_DEPENDENCIES = {
    "jsonschema",
    "pydantic",
    "pydantic-settings",
    "httpx",
    "typer",
    "jinja2",
}
```

Remove `"jsonschema"` from the `dev` set inside `EXPECTED_EXTRAS` (it is promoted to required):

```python
    "dev": {"pytest", "beautifulsoup4", "trafilatura", "pandas", "networkx", "tomli"},
```

Replace `test_core_package_has_no_runtime_dependencies_and_declares_license`:

```python
def test_required_dependencies_stay_pinned_to_the_allowlist():
    project = load_pyproject()["project"]

    assert {package_name(req) for req in project["dependencies"]} == EXPECTED_REQUIRED_DEPENDENCIES
    assert project["license"]["text"] == "AGPL-3.0-only"
    assert (KIT_ROOT / "LICENSE").exists()
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `PYTEST tests/quality/governance/platform/test_packaging_policy.py -q`
Expected: FAIL — `test_required_dependencies_stay_pinned_to_the_allowlist` (empty dependencies) and `test_optional_dependency_groups_are_intentional` (dev still has jsonschema).

- [ ] **Step 4: Update pyproject.toml**

```toml
dependencies = [
  "jsonschema>=4.20.0",
  "pydantic>=2.7",
  "pydantic-settings>=2.2",
  "httpx>=0.27",
  "typer>=0.12",
  "jinja2>=3.1",
]
```

and delete the `"jsonschema>=4.20.0",` line from the `dev` extra.

- [ ] **Step 5: Run tests to verify they pass**

Run: `PYTEST tests/quality/governance/platform/test_packaging_policy.py -q`
Expected: PASS (all tests in file).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml tests/quality/governance/platform/test_packaging_policy.py
git commit -m "feat(deps): adopt pinned required dependency set"
```

---

### Task 2: Package schemas as core.models package data

**Files:**
- Create: `src/core/models/schemas_data/README.md`
- Create: `src/core/models/schemas_data/{case,evidence,review}/*.json` (copies of `docs/schemas/`)
- Modify: `pyproject.toml` (`[tool.setuptools.package-data]`)
- Modify: `tests/quality/governance/platform/test_packaging_policy.py` (drift test)

**Interfaces:**
- Produces: `files("core.models") / "schemas_data" / "<group>/<name>.schema.json"` resolvable in installed packages; `SCHEMA_SHARDS` tuple in the packaging test.

- [ ] **Step 1: Write the failing drift test**

In `test_packaging_policy.py`, below `REGISTRY_SHARDS`, add:

```python
SCHEMA_SHARDS = (
    "case/artifact.schema.json",
    "case/entity.schema.json",
    "case/place.schema.json",
    "case/source.schema.json",
    "evidence/claim.schema.json",
    "evidence/event.schema.json",
    "evidence/event_link.schema.json",
    "evidence/relationship.schema.json",
    "review/quote.schema.json",
    "review/redaction.schema.json",
    "review/research_action.schema.json",
    "review/source_span.schema.json",
)
```

and next to `test_packaged_registry_data_matches_canonical_docs_registry`:

```python
def test_packaged_schema_data_matches_canonical_docs_schemas():
    docs_schemas = KIT_ROOT / "docs" / "schemas"
    package_schemas = KIT_ROOT / "src" / "core" / "models" / "schemas_data"

    for rel in SCHEMA_SHARDS:
        assert json.loads((package_schemas / rel).read_text(encoding="utf-8")) == json.loads(
            (docs_schemas / rel).read_text(encoding="utf-8")
        )
```

- [ ] **Step 2: Run it to verify it fails**

Run: `PYTEST tests/quality/governance/platform/test_packaging_policy.py::test_packaged_schema_data_matches_canonical_docs_schemas -q`
Expected: FAIL with `FileNotFoundError` (schemas_data does not exist).

- [ ] **Step 3: Copy the schemas and add the data README**

```bash
mkdir -p src/core/models/schemas_data
cp -r docs/schemas/case docs/schemas/evidence docs/schemas/review src/core/models/schemas_data/
```

Create `src/core/models/schemas_data/README.md`:

```markdown
# Packaged record schemas

Read-only mirror of `docs/schemas/` shipped as package data so installed
packages can validate ledger records without a repo checkout. `docs/schemas/`
is canonical; `tests/quality/governance/platform/test_packaging_policy.py::
test_packaged_schema_data_matches_canonical_docs_schemas` keeps this copy in
sync. Edit the canonical files and re-copy; never edit these directly.
```

- [ ] **Step 4: Register the package data in pyproject.toml**

In `[tool.setuptools.package-data]` add:

```toml
"core.models" = [
  "schemas_data/case/*.json",
  "schemas_data/evidence/*.json",
  "schemas_data/review/*.json",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `PYTEST tests/quality/governance/platform/test_packaging_policy.py -q`
Expected: PASS.

Run: `PYTEST tests/quality/governance/test_repository_shape.py -q`
Expected: PASS (schemas_data has 1 direct file + 3 child dirs, each child ≤4 files).

- [ ] **Step 6: Commit**

```bash
git add src/core/models/schemas_data pyproject.toml tests/quality/governance/platform/test_packaging_policy.py
git commit -m "feat(schemas): package record schemas as core.models data"
```

---

### Task 3: Resolve schemas via importlib.resources

**Files:**
- Modify: `src/adapters/ops/casework/records/validation.py:28-48` (`load_schema`)
- Test: `tests/runtime/unit/ops/test_schema_loading.py` (create)

**Interfaces:**
- Consumes: packaged `schemas_data` from Task 2.
- Produces: `load_schema(schema_name: str) -> dict[str, Any] | None` — same signature, resolution order becomes repo checkout `docs/schemas/` (dev) then `files("core.models")/"schemas_data"` (installed). `SCHEMA_BY_RECORD` unchanged.

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/unit/ops/test_schema_loading.py`:

```python
"""Schema resolution works from any CWD and without a repo checkout."""

from __future__ import annotations

import os
from pathlib import Path

from adapters.ops.casework.records.validation import SCHEMA_BY_RECORD, load_schema


def test_every_record_schema_resolves(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # far away from the repo checkout
    for record_name, schema_name in SCHEMA_BY_RECORD.items():
        schema = load_schema(schema_name)
        assert schema is not None, f"missing schema for {record_name}"
        assert schema.get("type") == "object"
        assert "required" in schema


def test_unknown_schema_returns_none():
    assert load_schema("nonexistent.schema.json") is None
```

- [ ] **Step 2: Run it to verify current behavior fails**

Run: `PYTEST tests/runtime/unit/ops/test_schema_loading.py -q`
Expected: `test_every_record_schema_resolves` FAILS — the current CWD/parent walk from `tmp_path` finds no schemas. (If it passes because `Path(__file__)` parents reach the repo, proceed anyway: the point of the rewrite is removing the guesswork; keep the test.)

- [ ] **Step 3: Rewrite load_schema**

Replace `load_schema` in `validation.py` (drop the old roots/schema_dirs walk entirely):

```python
from importlib.resources import files

_SCHEMA_GROUPS = ("case", "evidence", "review")


def _schema_roots():
    checkout = Path(__file__).resolve().parents[5] / "docs" / "schemas"
    roots = []
    if checkout.exists():
        roots.append(checkout)
    roots.append(files("core.models").joinpath("schemas_data"))
    return roots


def load_schema(schema_name: str) -> dict[str, Any] | None:
    for root in _schema_roots():
        for group in _SCHEMA_GROUPS:
            candidate = root.joinpath(group).joinpath(schema_name) if not isinstance(root, Path) else root / group / schema_name
            try:
                if candidate.is_file():
                    return json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, AttributeError):
                continue
    return None
```

Note: `parents[5]` from `src/adapters/ops/casework/records/validation.py` is the repo root — verify with `python -c "from pathlib import Path; print(Path('src/adapters/ops/casework/records/validation.py').resolve().parents[5])"` before relying on it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTEST tests/runtime/unit/ops/test_schema_loading.py tests/runtime/integration/operations -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adapters/ops/casework/records/validation.py tests/runtime/unit/ops/test_schema_loading.py
git commit -m "fix(validation): resolve schemas via importlib.resources"
```

---

### Task 4: jsonschema-first validate_case

**Files:**
- Modify: `src/adapters/ops/casework/records/validation.py` (`required_errors`, `validate_case`)
- Test: `tests/runtime/integration/operations/case/test_validate_schemas.py` (create)

**Interfaces:**
- Consumes: `load_schema` from Task 3.
- Produces: `validate_case(case_dir) -> list[str]` — same signature; errors formatted `f"{record_name}[{idx}] {path}: {message}"` where `idx` is the 1-based JSONL line and `path` is the JSON-pointer-ish field path (or `<record>` for record-level errors). `required_errors` is deleted.

- [ ] **Step 1: Write the failing tests**

Create `tests/runtime/integration/operations/case/test_validate_schemas.py`:

```python
"""validate_case enforces the real JSON Schemas, line-addressed."""

from __future__ import annotations

import json
from pathlib import Path

from adapters.ops.casework.records.validation import validate_case

SYNTHETIC_CASE = Path(__file__).resolve().parents[5] / "data" / "examples" / "synthetic_case"


def _seed_case(tmp_path: Path, record_file: str, rows: list[dict]) -> Path:
    case = tmp_path / "case"
    (case / "records").mkdir(parents=True)
    (case / "case.json").write_text(json.dumps({"case_id": "t"}), encoding="utf-8")
    text = "".join(json.dumps(row) + "\n" for row in rows)
    (case / "records" / record_file).write_text(text, encoding="utf-8")
    return case


def test_synthetic_case_fixture_validates_clean():
    assert validate_case(SYNTHETIC_CASE) == []


def test_missing_required_field_is_line_addressed(tmp_path):
    case = _seed_case(tmp_path, "claims.jsonl", [{"claim_id": "c1", "claim": "x"}])
    errors = validate_case(case)
    assert any(e.startswith("claims[1] ") and "required" in e for e in errors)


def test_enum_violation_is_reported_with_field_path(tmp_path):
    case = _seed_case(
        tmp_path,
        "claims.jsonl",
        [{"claim_id": "c1", "claim": "x", "status": "definitely_true", "confidence": 0.5, "source_ids": ["s1"]}],
    )
    errors = validate_case(case)
    assert any(e.startswith("claims[1] status: ") for e in errors)
```

- [ ] **Step 2: Run to verify the new expectations fail**

Run: `PYTEST tests/runtime/integration/operations/case/test_validate_schemas.py -q`
Expected: `test_enum_violation_is_reported_with_field_path` FAILS (current format is `claims[1] schema error: <long message>` and only when jsonschema import succeeded). `test_synthetic_case_fixture_validates_clean` should pass already — if it fails, STOP and report: the fixture or a schema needs attention before proceeding, and that decision belongs to the operator.

- [ ] **Step 3: Rewrite validation to be jsonschema-first**

In `validation.py`: delete `required_errors` entirely, add `import jsonschema` at module top (it is a required dependency now), and replace `validate_case`:

```python
def _row_errors(record_name: str, schema: dict[str, Any], row: dict[str, Any], idx: int) -> list[str]:
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(row), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(part) for part in error.absolute_path) or "<record>"
        errors.append(f"{record_name}[{idx}] {path}: {error.message}")
    return errors


def validate_case(case_dir: str | Path) -> list[str]:
    ensure_case(case_dir)
    errors: list[str] = []
    for record_name in RECORD_FILES:
        rows = read_jsonl(record_path(case_dir, record_name))
        schema = load_schema(SCHEMA_BY_RECORD[record_name])
        if schema is None:
            errors.append(f"{record_name}: schema {SCHEMA_BY_RECORD[record_name]} not found")
            continue
        for idx, row in enumerate(rows, start=1):
            errors.extend(_row_errors(record_name, schema, row, idx))
    return errors
```

Remove the now-unused `argparse` import only if `validate(args)` no longer needs it (it does — `validate(args: argparse.Namespace)` stays; leave the import).

Performance note: construct the validator once per record file if the loop feels slow — `Draft202012Validator(schema)` hoisted above the row loop is fine and preferred.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTEST tests/runtime/integration/operations/case/test_validate_schemas.py tests/runtime/integration/operations -q`
Expected: PASS.

- [ ] **Step 5: End-to-end check against the ledger CLI**

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- crk-ledger validate data/examples/synthetic_case
```

Expected: `Validation passed for .../data/examples/synthetic_case`.

- [ ] **Step 6: Commit**

```bash
git add src/adapters/ops/casework/records/validation.py tests/runtime/integration/operations/case/test_validate_schemas.py
git commit -m "feat(validation): enforce record schemas with jsonschema"
```

---

### Task 5: Pydantic record models

**Files:**
- Create: `src/core/models/records/__init__.py`
- Create: `src/core/models/records/case.py`
- Create: `src/core/models/records/evidence.py`
- Create: `src/core/models/records/review.py`
- Create: `src/core/models/records/README.md`
- Test: `tests/runtime/unit/models/test_record_models.py` (create; add `tests/runtime/unit/models/__init__.py` only if sibling dirs have one — check first)

**Interfaces:**
- Produces: `from core.models.records import MODEL_BY_RECORD, ClaimRecord, SourceRecord, ...`; `MODEL_BY_RECORD: dict[str, type[BaseModel]]` keyed by the `RECORD_FILES` record names. Every model: `model_config = ConfigDict(extra="allow")`, optional fields default `None`, `.model_dump(exclude_none=True)` round-trips a ledger row.

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/unit/models/test_record_models.py`:

```python
"""Record models parse real ledger rows and reject schema violations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.casefile import RECORD_FILES
from core.models.records import MODEL_BY_RECORD, ClaimRecord

SYNTHETIC_RECORDS = Path(__file__).resolve().parents[4] / "data" / "examples" / "synthetic_case" / "records"


def test_model_map_covers_every_record_type():
    assert set(MODEL_BY_RECORD) == set(RECORD_FILES)


def test_models_parse_every_synthetic_case_row():
    for record_name, filename in RECORD_FILES.items():
        path = SYNTHETIC_RECORDS / filename
        if not path.exists():
            continue
        model = MODEL_BY_RECORD[record_name]
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                model.model_validate(json.loads(line))


def test_missing_required_field_rejected():
    with pytest.raises(ValidationError):
        ClaimRecord.model_validate({"claim_id": "c1", "claim": "x"})


def test_extra_fields_survive_round_trip():
    row = {
        "claim_id": "c1",
        "claim": "x",
        "status": "unverified",
        "confidence": 0.2,
        "source_ids": ["s1"],
        "custom_field": "kept",
    }
    assert ClaimRecord.model_validate(row).model_dump(exclude_none=True) == row
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTEST tests/runtime/unit/models/test_record_models.py -q`
Expected: FAIL with `ModuleNotFoundError: core.models.records`.

- [ ] **Step 3: Create the model modules**

`src/core/models/records/case.py` — field lists transcribed from `docs/schemas/case/*.json` (required fields have no default; everything else defaults to `None`):

```python
"""Typed models for case-scope records: sources, entities, places, artifacts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

SourceType = Literal[
    "news_article", "eyewitness_account", "court_record", "government_record",
    "official_report", "interview", "memoir", "book", "documentary", "academic",
    "archive", "social_media_lead", "other",
]
ReliabilityGrade = Literal["A", "B", "C", "D", "X"]


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_id: str
    title: str
    source_type: SourceType
    reliability_grade: ReliabilityGrade
    date_accessed: str
    author: str | None = None
    publisher: str | None = None
    date_published: str | None = None
    url: str | None = None
    archive_url: str | None = None
    raw_path: str | None = None
    text_path: str | None = None
    content_type: str | None = None
    capture_method: Literal["ingest_url", "manual_registration", "archive_lookup", "local_file", "registered_source"] | None = None
    capture_timestamp: str | None = None
    preservation_checked_at: str | None = None
    raw_sha256: str | None = None
    text_sha256: str | None = None
    raw_size_bytes: int | None = None
    text_size_bytes: int | None = None
    preservation_status: Literal["captured", "registered_with_archive", "metadata_only", "missing_artifacts"] | None = None
    preservation_warnings: list[str] | None = None
    independence_group: str | None = None
    notes: str | None = None
    public_export: bool | None = None


class EntityRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    entity_id: str
    entity_type: Literal[
        "person", "organization", "group", "institution", "publication", "place_alias",
        "object", "vehicle", "document", "recording", "event_series", "other",
    ]
    name: str
    status: Literal["confirmed", "candidate", "excluded", "merged"]
    source_ids: list[str]
    display_name: str | None = None
    aliases: list[str] | None = None
    role_tags: list[str] | None = None
    privacy_level: Literal["public_figure", "limited_purpose_public", "private_person", "minor", "not_applicable", "unknown"] | None = None
    living_status: Literal["living", "deceased", "unknown", "not_applicable"] | None = None
    claim_ids: list[str] | None = None
    public_export: bool | None = None
    notes: str | None = None


class PlaceRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    place_id: str
    name: str
    source_ids: list[str]
    place_type: str | None = None
    admin_area: str | None = None
    country: str | None = None
    lat: float | None = None
    lon: float | None = None
    precision: Literal["exact", "approximate", "city_only", "region_only", "unknown"] | None = None
    privacy_sensitive: bool | None = None
    public_export: bool | None = None
    notes: str | None = None


class ArtifactRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    artifact_id: str
    artifact_type: Literal[
        "document", "letter", "photo", "recording", "vehicle", "object",
        "weapon_public_record", "digital_file", "book", "publication", "other",
    ]
    name: str
    source_ids: list[str]
    description: str | None = None
    source_span_ids: list[str] | None = None
    claim_ids: list[str] | None = None
    sensitivity: Literal["low", "medium", "high", "exclude"] | None = None
    public_export: bool | None = None
    notes: str | None = None
```

`src/core/models/records/evidence.py` — from `docs/schemas/evidence/*.json`:

```python
"""Typed models for evidence records: claims, events, event links, relationships."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

EvidenceStatus = Literal["verified", "corroborated", "single_source", "disputed", "unverified", "excluded"]
RelationshipClass = Literal[
    "documented_successor", "method_diffusion", "personnel_bridge",
    "narrative_inheritance", "contested_overlap", "hypothesis_requires_more_sources",
]


class ClaimRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    claim_id: str
    claim: str
    status: Literal[
        "verified", "corroborated", "single_source", "disputed", "unverified",
        "false_or_retracted", "excluded_from_public_script",
    ]
    confidence: float
    source_ids: list[str]
    claim_type: Literal[
        "identity", "timeline", "relationship", "event", "location", "motive",
        "quote", "background", "legal", "eyewitness", "other",
    ] | None = None
    assertion_type: Literal[
        "source_stated_fact", "allegation", "denial", "court_finding",
        "self_report", "biography_claim", "lead_only", "expert_context",
    ] | None = None
    source_span_ids: list[str] | None = None
    contradicts: list[str] | None = None
    supports: list[str] | None = None
    privacy_review: Literal["clear", "needs_review", "redact", "exclude"] | None = None
    public_export: bool | None = None
    notes: str | None = None


class EventRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str
    title: str
    event_type: str
    source_ids: list[str]
    start_date: str | None = None
    end_date: str | None = None
    date_precision: Literal["exact", "day", "month", "year", "decade", "approximate", "unknown"] | None = None
    place_ids: list[str] | None = None
    entity_ids: list[str] | None = None
    artifact_ids: list[str] | None = None
    claim_ids: list[str] | None = None
    source_span_ids: list[str] | None = None
    confidence: float | None = None
    status: EvidenceStatus | None = None
    public_export: bool | None = None
    notes: str | None = None


class EventLinkRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_link_id: str
    entity_id: str
    event_id: str
    relation_type: str
    source_ids: list[str]
    relationship_class: RelationshipClass | None = None
    basis: str | None = None
    claim_ids: list[str] | None = None
    source_span_ids: list[str] | None = None
    confidence: float | None = None
    status: EvidenceStatus | None = None
    public_export: bool | None = None
    notes: str | None = None


class RelationshipRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    rel_id: str
    src_entity_id: str
    dst_entity_id: str
    relation_type: str
    source_ids: list[str]
    relationship_class: RelationshipClass | None = None
    start_date: str | None = None
    end_date: str | None = None
    claim_ids: list[str] | None = None
    source_span_ids: list[str] | None = None
    confidence: float | None = None
    status: EvidenceStatus | None = None
    public_export: bool | None = None
    notes: str | None = None
```

`src/core/models/records/review.py` — from `docs/schemas/review/*.json`:

```python
"""Typed models for review records: source spans, quotes, research actions, redactions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class SourceSpanRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_span_id: str
    source_id: str
    locator_type: Literal[
        "page", "page_range", "timestamp", "timestamp_range", "line_range",
        "paragraph", "section", "char_range", "byte_range", "url_fragment", "other",
    ]
    locator: Any
    exact_text: str | None = None
    summary: str | None = None
    public_export: bool | None = None
    notes: str | None = None


class QuoteRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    quote_id: str
    source_id: str
    exact_quote: str
    speaker: str | None = None
    page_or_timestamp: str | None = None
    source_span_ids: list[str] | None = None
    supports_claim_ids: list[str] | None = None
    account_type: Literal["firsthand", "secondhand", "unclear", "not_applicable"] | None = None
    public_export: bool | None = None
    notes: str | None = None


class ResearchActionRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    timestamp: str
    action: str
    details: dict[str, Any]
    notes: str | None = None


class RedactionRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    redaction_id: str
    record_id: str
    reason: str
    field: str | None = None
    public_replacement: str | None = None
    source_ids: list[str] | None = None
    notes: str | None = None
```

`src/core/models/records/__init__.py`:

```python
"""Pydantic models mirroring the canonical record schemas in docs/schemas/."""

from __future__ import annotations

from pydantic import BaseModel

from .case import ArtifactRecord, EntityRecord, PlaceRecord, SourceRecord
from .evidence import ClaimRecord, EventLinkRecord, EventRecord, RelationshipRecord
from .review import QuoteRecord, RedactionRecord, ResearchActionRecord, SourceSpanRecord

MODEL_BY_RECORD: dict[str, type[BaseModel]] = {
    "sources": SourceRecord,
    "entities": EntityRecord,
    "places": PlaceRecord,
    "artifacts": ArtifactRecord,
    "claims": ClaimRecord,
    "events": EventRecord,
    "event_links": EventLinkRecord,
    "relationships": RelationshipRecord,
    "source_spans": SourceSpanRecord,
    "quotes": QuoteRecord,
    "research_actions": ResearchActionRecord,
    "redactions": RedactionRecord,
}

__all__ = ["MODEL_BY_RECORD", *(model.__name__ for model in MODEL_BY_RECORD.values())]
```

`src/core/models/records/README.md`:

```markdown
# Record models

Pydantic `BaseModel` classes mirroring `docs/schemas/` — the typed in-memory
representation for ledger rows. The JSON Schemas stay canonical for on-disk
validation; `tests/quality/governance/platform/test_model_schema_drift.py`
keeps required fields, property names, and enums aligned. `extra="allow"` and
`model_dump(exclude_none=True)` preserve round-trip fidelity for rows carrying
fields the schemas allow via `additionalProperties`.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTEST tests/runtime/unit/models/test_record_models.py -q`
Expected: PASS. If `test_models_parse_every_synthetic_case_row` fails on a fixture row, the model field is wrong, not the fixture — recheck the schema transcription.

Run: `PYTEST tests/quality/governance/test_repository_shape.py -q`
Expected: PASS (`core/models` now has 3 direct files + 2 child dirs: `records/`, `schemas_data/`).

- [ ] **Step 5: Commit**

```bash
git add src/core/models/records tests/runtime/unit/models
git commit -m "feat(models): add pydantic record models for the ledger"
```

---

### Task 6: Model↔schema drift governance test

**Files:**
- Create: `tests/quality/governance/platform/test_model_schema_drift.py`

**Interfaces:**
- Consumes: `MODEL_BY_RECORD` (Task 5), `SCHEMA_BY_RECORD`/`load_schema` (Task 3).

- [ ] **Step 1: Write the drift test**

```python
"""Governance: pydantic record models stay aligned with the canonical schemas."""

from __future__ import annotations

import types
import typing

import pytest

from adapters.ops.casework.records.validation import SCHEMA_BY_RECORD, load_schema
from core.models.records import MODEL_BY_RECORD


def _literal_values(annotation) -> set[str] | None:
    """Collect Literal values from an annotation, unwrapping Optional/Union."""
    origin = typing.get_origin(annotation)
    if origin is typing.Literal:
        return set(typing.get_args(annotation))
    if origin in (typing.Union, types.UnionType):
        values: set[str] = set()
        found = False
        for arg in typing.get_args(annotation):
            if arg is type(None):
                continue
            sub = _literal_values(arg)
            if sub is not None:
                values |= sub
                found = True
        return values if found else None
    return None


@pytest.mark.parametrize("record_name", sorted(MODEL_BY_RECORD))
def test_model_matches_schema(record_name):
    schema = load_schema(SCHEMA_BY_RECORD[record_name])
    assert schema is not None
    model = MODEL_BY_RECORD[record_name]

    schema_fields = set(schema["properties"])
    model_fields = set(model.model_fields)
    assert model_fields == schema_fields, f"{record_name}: field mismatch"

    schema_required = set(schema["required"])
    model_required = {name for name, f in model.model_fields.items() if f.is_required()}
    assert model_required == schema_required, f"{record_name}: required mismatch"

    for name, prop in schema["properties"].items():
        enum = prop.get("enum")
        if not enum:
            continue
        literals = _literal_values(model.model_fields[name].annotation)
        assert literals == {v for v in enum if v is not None}, f"{record_name}.{name}: enum mismatch"
```

- [ ] **Step 2: Run to verify it passes (and catches drift)**

Run: `PYTEST tests/quality/governance/platform/test_model_schema_drift.py -q`
Expected: PASS for all 12 record types. Sanity-check the test bites: temporarily delete `notes` from `RedactionRecord`, re-run, confirm FAIL, restore.

- [ ] **Step 3: Commit**

```bash
git add tests/quality/governance/platform/test_model_schema_drift.py
git commit -m "test(governance): pin record models to canonical schemas"
```

---

### Task 7: OpResult as a pydantic model

**Files:**
- Modify: `src/adapters/ops/result.py`
- Test: existing `tests/runtime/unit/ops/test_result.py` must keep passing unchanged.

**Interfaces:**
- Produces: `OpResult(BaseModel)` — same field names/defaults, keyword construction, and `to_dict()` behavior as the dataclass. `local_op` unchanged.

- [ ] **Step 1: Confirm no positional construction exists**

```bash
grep -rn "OpResult(" src tests --include='*.py' | grep -v "name=" | grep -v "class OpResult" | grep -v "type\[OpResult\]"
```

Expected: no output. If any positional call sites appear, convert them to keyword arguments first (pydantic models are keyword-only).

- [ ] **Step 2: Convert the dataclass**

Replace the body of `src/adapters/ops/result.py`:

```python
"""Shared operation result type for the ops core."""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field

from core.casefile import CasefileError


class OpResult(BaseModel):
    """Uniform result for every case operation across CLI, graph, and MCP."""

    name: str
    ok: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    command: list[str] = Field(default_factory=list)
    dry_run: bool = False
    skipped: bool = False
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


def local_op(
    name: str,
    func: Callable[..., dict[str, Any]],
    /,
    *args: Any,
    **kwargs: Any,
) -> OpResult:
    """Run a Python-native case operation, mapping CasefileError to a failed result."""
    try:
        data = func(*args, **kwargs)
    except CasefileError as exc:
        return OpResult(name=name, ok=False, errors=[str(exc)])
    return OpResult(name=name, data=data)
```

- [ ] **Step 3: Run the ops and pipeline suites**

Run: `PYTEST tests/runtime/unit/ops tests/runtime/integration -q`
Expected: PASS. Watch for mutation patterns (`result.data["x"] = ...` is fine; `result.extra_attr = ...` would now raise — fix any such site by adding the data through `data`).

- [ ] **Step 4: Commit**

```bash
git add src/adapters/ops/result.py
git commit -m "refactor(ops): move OpResult to pydantic BaseModel"
```

---

### Task 8: CrkSettings at process boundaries

**Files:**
- Modify: `src/core/config.py` (full rewrite)
- Modify: `src/cli.py:12,148,168-199` (settings construction + value passing)
- Modify: `src/adapters/interfaces/mcp/context.py` (ServerContext gains settings)
- Modify: `src/adapters/ops/evidence/query.py:13-14`, `src/adapters/ops/casework/sources.py:12,103`, `src/core/memory/providers/mem0_provider.py:8-14,40-52`, `src/adapters/interfaces/llm/provider.py:5,26-27`
- Test: `tests/runtime/unit/core/test_settings.py` (create), plus a governance grep test inside it.

**Interfaces:**
- Produces: `core.config.CrkSettings(BaseSettings)` with fields `model_spec, searxng_url, qdrant_url, qdrant_host, qdrant_port, embed_model, mem0_llm_provider, mem0_llm_model, embedder_provider` reading env names `CRK_MODEL, CRK_SEARXNG_URL, CRK_QDRANT_URL, CRK_QDRANT_HOST, CRK_QDRANT_PORT, CRK_EMBED_MODEL, CRK_MEM0_LLM_PROVIDER, CRK_MEM0_LLM_MODEL, CRK_EMBEDDER_PROVIDER`. `DEFAULT_*` constants keep their current names/values. The per-key resolver functions (`model_spec()`, `searxng_url()`, …) are deleted.

- [ ] **Step 1: Write the failing tests**

Create `tests/runtime/unit/core/test_settings.py`:

```python
"""CrkSettings is the single env reader; core stays env-free."""

from __future__ import annotations

import subprocess
from pathlib import Path

from core.config import (
    DEFAULT_MODEL_SPEC,
    DEFAULT_QDRANT_PORT,
    DEFAULT_SEARXNG_URL,
    CrkSettings,
)

SRC = Path(__file__).resolve().parents[4] / "src"


def test_defaults_match_constants(monkeypatch):
    for var in ("CRK_MODEL", "CRK_SEARXNG_URL", "CRK_QDRANT_PORT"):
        monkeypatch.delenv(var, raising=False)
    settings = CrkSettings()
    assert settings.model_spec == DEFAULT_MODEL_SPEC
    assert settings.searxng_url == DEFAULT_SEARXNG_URL
    assert settings.qdrant_port == DEFAULT_QDRANT_PORT


def test_env_names_are_preserved(monkeypatch):
    monkeypatch.setenv("CRK_MODEL", "ollama:test-model")
    monkeypatch.setenv("CRK_QDRANT_PORT", "7777")
    settings = CrkSettings()
    assert settings.model_spec == "ollama:test-model"
    assert settings.qdrant_port == 7777


def test_settings_stay_at_process_boundaries():
    hits = subprocess.run(
        ["grep", "-rln", "CrkSettings(", str(SRC / "core"), str(SRC / "pipeline"), str(SRC / "adapters" / "ops")],
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    allowed = {str(SRC / "core" / "config.py")}
    assert set(hits) <= allowed, f"Settings() constructed deep in core: {hits}"
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTEST tests/runtime/unit/core/test_settings.py -q`
Expected: FAIL with `ImportError: cannot import name 'CrkSettings'`.

- [ ] **Step 3: Rewrite core/config.py**

```python
"""Runtime defaults for self-hosted CRK services, resolved once at process boundaries."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MODEL_SPEC = "ollama:llama3.1"
DEFAULT_SEARXNG_URL = "http://localhost:8080"
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_QDRANT_HOST = "localhost"
DEFAULT_QDRANT_PORT = 6333
DEFAULT_EMBED_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_MEM0_LLM_PROVIDER = "ollama"
DEFAULT_MEM0_LLM_MODEL = "llama3.1"
DEFAULT_EMBEDDER_PROVIDER = "huggingface"


class CrkSettings(BaseSettings):
    """Environment-backed service configuration. Construct once at CLI/MCP startup."""

    model_config = SettingsConfigDict(protected_namespaces=(), extra="ignore")

    model_spec: str = Field(default=DEFAULT_MODEL_SPEC, validation_alias="CRK_MODEL")
    searxng_url: str = Field(default=DEFAULT_SEARXNG_URL, validation_alias="CRK_SEARXNG_URL")
    qdrant_url: str = Field(default=DEFAULT_QDRANT_URL, validation_alias="CRK_QDRANT_URL")
    qdrant_host: str = Field(default=DEFAULT_QDRANT_HOST, validation_alias="CRK_QDRANT_HOST")
    qdrant_port: int = Field(default=DEFAULT_QDRANT_PORT, validation_alias="CRK_QDRANT_PORT")
    embed_model: str = Field(default=DEFAULT_EMBED_MODEL, validation_alias="CRK_EMBED_MODEL")
    mem0_llm_provider: str = Field(default=DEFAULT_MEM0_LLM_PROVIDER, validation_alias="CRK_MEM0_LLM_PROVIDER")
    mem0_llm_model: str = Field(default=DEFAULT_MEM0_LLM_MODEL, validation_alias="CRK_MEM0_LLM_MODEL")
    embedder_provider: str = Field(default=DEFAULT_EMBEDDER_PROVIDER, validation_alias="CRK_EMBEDDER_PROVIDER")
```

Empty-string env values: the old `env_str` treated `CRK_X=""` as unset. If any test depends on that, add a field validator; otherwise accept the (more standard) pydantic behavior and note it in the commit message.

- [ ] **Step 4: Update the deep modules to constant fallbacks**

`src/adapters/ops/evidence/query.py` — replace lines 13-14:

```python
from core.config import DEFAULT_EMBED_MODEL, DEFAULT_QDRANT_URL
```

and inside the index/query functions replace `default_embed_model(embed_model)` → `embed_model or DEFAULT_EMBED_MODEL` and `default_qdrant_url(qdrant_url)` → `qdrant_url or DEFAULT_QDRANT_URL` (locate with `grep -n "default_embed_model\|default_qdrant_url" src/adapters/ops/evidence/query.py`).

`src/adapters/ops/casework/sources.py` — replace line 12 with `from core.config import DEFAULT_SEARXNG_URL` and line 103's `default_searxng_url(searxng_url)` → `searxng_url or DEFAULT_SEARXNG_URL`.

`src/core/memory/providers/mem0_provider.py` — replace the six `from core.config import ... as default_*` imports with:

```python
from core.config import (
    DEFAULT_EMBED_MODEL,
    DEFAULT_EMBEDDER_PROVIDER,
    DEFAULT_MEM0_LLM_MODEL,
    DEFAULT_MEM0_LLM_PROVIDER,
    DEFAULT_QDRANT_HOST,
    DEFAULT_QDRANT_PORT,
)
```

and in the `config` dict: `default_qdrant_host(qdrant_host)` → `qdrant_host or DEFAULT_QDRANT_HOST`, `default_qdrant_port(qdrant_port)` → `qdrant_port if qdrant_port is not None else DEFAULT_QDRANT_PORT`, `default_mem0_llm_provider(llm_provider)` → `llm_provider or DEFAULT_MEM0_LLM_PROVIDER`, `default_mem0_llm_model(llm_model)` → `llm_model or DEFAULT_MEM0_LLM_MODEL`, `default_embedder_provider(embedder_provider)` → `embedder_provider or DEFAULT_EMBEDDER_PROVIDER`, `default_embed_model(embedder_model)` → `embedder_model or DEFAULT_EMBED_MODEL`.

`src/adapters/interfaces/llm/provider.py` — replace line 5 (`from core.config import DEFAULT_MODEL_SPEC, model_spec`) with `from core.config import DEFAULT_MODEL_SPEC`, then make exactly two function-body edits, leaving the rest of each function untouched:

```python
# old
def active_model_spec() -> tuple[str, str]:
    return parse_model_spec(model_spec())

# new
def active_model_spec(spec: str | None = None) -> tuple[str, str]:
    return parse_model_spec(spec or DEFAULT_MODEL_SPEC)
```

```python
# old (first line of get_chat_model's body)
    provider, model = parse_model_spec(spec) if spec else active_model_spec()

# new
    provider, model = parse_model_spec(spec or DEFAULT_MODEL_SPEC)
```

- [ ] **Step 5: Thread settings from the boundaries**

`src/cli.py` — in `main()` (or the top of command dispatch), construct once:

```python
from core.config import CrkSettings

settings = CrkSettings()
```

and replace each resolver call: `config.searxng_url(args.searxng_url)` → `args.searxng_url or settings.searxng_url`; `config.qdrant_url(args.qdrant_url)` → `args.qdrant_url or settings.qdrant_url`; `config.embed_model(args.embed_model)` → `args.embed_model or settings.embed_model`; `config.qdrant_host(args.qdrant_host)` → `args.qdrant_host or settings.qdrant_host`; `config.qdrant_port(args.qdrant_port)` → `args.qdrant_port if args.qdrant_port is not None else settings.qdrant_port`; `config.mem0_llm_provider(args.llm_provider)` → `args.llm_provider or settings.mem0_llm_provider`; `config.mem0_llm_model(args.llm_model)` → `args.llm_model or settings.mem0_llm_model`; `config.embedder_provider(args.embedder_provider)` → `args.embedder_provider or settings.embedder_provider`; `config.embed_model(args.embedder_model)` → `args.embedder_model or settings.embed_model`. The `settings` instance must be reachable where commands resolve args — if commands are module-level functions receiving `args`, resolve settings once at module import is NOT acceptable (import-time env read); pass it via the command context or construct in `main()` and attach to `args` (e.g., `args.settings = settings`) before dispatch.

Preserve CRK_MODEL for LLM-enabled runs: where `cli.py` invokes `run_case_builder(...)` with `llm_enabled=True` state, pass `model_spec=settings.model_spec`; add a `model_spec: str | None = None` keyword to `run_case_builder` and `resume_case_builder` in `src/pipeline/app/service.py` and thread it into `_model_factory`:

```python
def _model_factory(llm_enabled: bool, model_spec: str | None = None):
    if not llm_enabled:
        return None
    from adapters.interfaces.llm.provider import get_chat_model

    def factory(spec: str | None = None):
        return get_chat_model(spec or model_spec)

    return factory
```

(Check how the existing factory is invoked in `pipeline/graph/` — `grep -rn "model_factory" src/pipeline/` — and keep the call signature the callers expect.)

`src/adapters/interfaces/mcp/context.py` — add settings to the context:

```python
from core.config import CrkSettings


@dataclass
class ServerContext:
    repo_root: Path
    cases_root: Path
    runner: CrkRunner
    settings: CrkSettings
    skill_root: Path | None = None


def default_context() -> ServerContext:
    repo_root = default_repo_root()
    cases_root = Path(os.environ.get("CRK_CASES_ROOT") or repo_root / "data" / "cases")
    return ServerContext(
        repo_root=repo_root,
        cases_root=cases_root,
        runner=CrkRunner(repo_root=repo_root, dry_run=False),
        settings=CrkSettings(),
        skill_root=default_skill_root(repo_root),
    )
```

Then `grep -rn "qdrant\|embed_model\|searxng\|discover\|query_case\|index_case" src/adapters/interfaces/mcp/tools/` and pass `ctx.settings.<field>` at any tool call site that reaches `query.py`/`sources.py` without explicit values (e.g., `query_ops.query_case(..., qdrant_url=ctx.settings.qdrant_url, embed_model=ctx.settings.embed_model)`). If no MCP tool exposes those ops, no change is needed — note that in the commit message.

- [ ] **Step 6: Verify nothing deep still imports the deleted resolvers**

```bash
grep -rn "from core.config import" src --include='*.py'
grep -rn "config\.\(model_spec\|searxng_url\|qdrant_url\|qdrant_host\|qdrant_port\|embed_model\|mem0_llm\|embedder_provider\)(" src --include='*.py'
```

Expected: first grep shows only `CrkSettings` / `DEFAULT_*` imports; second grep is empty.

- [ ] **Step 7: Run tests to verify they pass**

Run: `PYTEST tests/runtime/unit/core/test_settings.py tests/runtime -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/core/config.py src/cli.py src/pipeline/app/service.py src/adapters/interfaces/mcp/context.py src/adapters/interfaces/llm/provider.py src/adapters/ops/evidence/query.py src/adapters/ops/casework/sources.py src/core/memory/providers/mem0_provider.py tests/runtime/unit/core/test_settings.py
git commit -m "refactor(config): confine env reads to CrkSettings at process boundaries"
```

---

### Task 9: Documentation and changelog

**Files:**
- Modify: `CLAUDE.md` (Repo constraints bullet)
- Modify: `CHANGELOG.md` (`## [Unreleased]`)
- Modify: `src/core/models/README.md`, `src/adapters/ops/README.md` (only if they describe the dataclass/no-deps behavior — check first)

**Interfaces:** none (docs only).

- [ ] **Step 1: Update the CLAUDE.md constraint**

Replace the bullet beginning "The package has no required dependencies" with:

```markdown
- The package has a small pinned required-dependency set (`jsonschema`, `pydantic`, `pydantic-settings`, `httpx`, `typer`, `jinja2`) enforced by `tests/quality/governance/platform/test_packaging_policy.py`; do not add required dependencies without updating that allowlist deliberately. Heavier features stay behind the optional extras in `pyproject.toml` (`dev`, `agentic`, `mcp`, `documents`, `retrieval`, `memory-local`, `web-local`) and must degrade gracefully (import lazily, skip tests) when absent. Pydantic contract: `BaseModel` for records/packets/manifests/serialized artifacts; `BaseSettings` only at process boundaries (CLI/MCP startup), constructed once with values passed inward.
```

Also check `AGENTS.md` (`grep -n "stdlib\|no required" AGENTS.md`) and update any matching language the same way; as of planning it had none.

- [ ] **Step 2: Update CHANGELOG.md under `## [Unreleased]`**

```markdown
### Changed
- Adopted a pinned required-dependency set (`jsonschema`, `pydantic`, `pydantic-settings`, `httpx`, `typer`, `jinja2`); the core package is no longer stdlib-only.
- `crk-ledger validate` now enforces the full JSON Schemas (enums, types, nested shapes) with line-addressed errors, replacing required-field-only checks.
- Environment configuration is resolved once at CLI/MCP startup via `CrkSettings`; all `CRK_*` variable names and defaults are unchanged.

### Added
- Typed pydantic models for all twelve ledger record types (`core.models.records`), drift-tested against the canonical schemas.
- Record schemas ship as package data, so installed packages validate without a repo checkout.
```

- [ ] **Step 3: Check the two READMEs and update if stale**

```bash
grep -n "dataclass\|stdlib\|no required" src/adapters/ops/README.md src/core/models/README.md
```

If `src/adapters/ops/README.md` calls `OpResult` a dataclass, change the wording to "pydantic model". Keep both READMEs accurate to what shipped.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md CHANGELOG.md src/adapters/ops/README.md src/core/models/README.md
git commit -m "docs: record required-dependency contract and stage-1 changes"
```

---

### Task 10: Full verification

**Files:** none (verification only).

- [ ] **Step 1: Full check + suite**

```bash
moon run crk:check
moon run crk:test
```

Expected: both green. Governance lane includes repository shape, packaging policy, and the new drift tests.

- [ ] **Step 2: Exercise both CLIs end-to-end**

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- crk-ledger validate data/examples/synthetic_case
uv run --cache-dir .uv-cache --no-project --with-editable . -- cr-kit plan data/examples/synthetic_case
CRK_QDRANT_PORT=7777 uv run --cache-dir .uv-cache --no-project --with-editable . -- python -c "from core.config import CrkSettings; assert CrkSettings().qdrant_port == 7777; print('env ok')"
```

Expected: validation passes, plan prints a dry-run plan, `env ok`.

- [ ] **Step 3: Fresh-build smoke (packaging includes schemas)**

```bash
moon run crk:release-check
```

Expected: green — the fresh-build smoke imports the package and the packaged `schemas_data` resolves. If `release-check` includes tag checks that fail on an untagged branch, run the underlying fresh-build script directly (`deployment/scripts/checks/fresh_build.py`) and note it.

- [ ] **Step 4: Wrap up the branch**

Use the superpowers:finishing-a-development-branch skill to choose merge/PR handling back to `dev`. Do not push tags.
