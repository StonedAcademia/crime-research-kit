"""Governance: fixture schemas, provenance, and automation safety."""

from __future__ import annotations

import json
from pathlib import Path

from tests.helpers import KIT_ROOT


SCHEMA_BY_RECORD = {
    "artifacts": "case/artifact.schema.json",
    "claims": "evidence/claim.schema.json",
    "entities": "case/entity.schema.json",
    "event_links": "evidence/event_link.schema.json",
    "events": "evidence/event.schema.json",
    "places": "case/place.schema.json",
    "quotes": "review/quote.schema.json",
    "redactions": "review/redaction.schema.json",
    "relationships": "evidence/relationship.schema.json",
    "research_actions": "review/research_action.schema.json",
    "source_spans": "review/source_span.schema.json",
    "sources": "case/source.schema.json",
}
REQUIRED_BY_RECORD = {
    name: set(json.loads((KIT_ROOT / "docs" / "schemas" / schema).read_text()).get("required", []))
    for name, schema in SCHEMA_BY_RECORD.items()
}


def iter_example_records():
    for case_dir in sorted((KIT_ROOT / "data" / "examples").iterdir()):
        records = case_dir / "records"
        if not records.exists():
            continue
        for path in sorted(records.glob("*.jsonl")):
            record_type = path.stem
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.strip():
                    yield case_dir, record_type, path, lineno, json.loads(line)


def validate_required_shape(record_type: str, row: dict) -> list[str]:
    missing = sorted(REQUIRED_BY_RECORD.get(record_type, set()) - set(row))
    errors = [f"missing {field}" for field in missing]
    try:
        import jsonschema  # type: ignore
    except Exception:
        return errors
    schema_rel = SCHEMA_BY_RECORD.get(record_type)
    if schema_rel:
        try:
            jsonschema.validate(instance=row, schema=json.loads((KIT_ROOT / "docs" / "schemas" / schema_rel).read_text()))
        except Exception as exc:
            errors.append(str(exc))
    return errors


def test_example_records_validate_against_schemas():
    errors = []
    for _case_dir, record_type, path, lineno, row in iter_example_records():
        for error in validate_required_shape(record_type, row):
            errors.append(f"{path.relative_to(KIT_ROOT)}:{lineno} {error}")
    assert not errors, errors


def test_synthetic_claims_have_provenance_and_reliable_sources():
    case_dir = KIT_ROOT / "data" / "examples" / "synthetic_case"
    sources = [
        json.loads(line)
        for line in (case_dir / "records" / "sources.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    grades = {source["source_id"]: source.get("reliability_grade") for source in sources}
    errors = []
    for line in (case_dir / "records" / "claims.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        claim = json.loads(line)
        claim_id = claim.get("claim_id")
        source_ids = claim.get("source_ids") or []
        if not source_ids:
            errors.append(f"{claim_id}: missing source_ids")
        if "confidence" not in claim or "status" not in claim:
            errors.append(f"{claim_id}: missing confidence/status")
        missing = [source_id for source_id in source_ids if source_id not in grades]
        if missing:
            errors.append(f"{claim_id}: missing source rows {missing}")
        weak = [source_id for source_id in source_ids if grades.get(source_id) in {"", "D", "X"}]
        if weak:
            errors.append(f"{claim_id}: weak reliability path {weak}")
    assert not errors, errors


def test_automation_comentions_are_private_and_unverified():
    errors = []
    for case_dir, record_type, path, lineno, row in iter_example_records():
        if case_dir.name == "unsafe_case_fixture":
            continue
        if record_type not in {"relationships", "event_links"}:
            continue
        relation = str(row.get("relation_type", "")).casefold()
        if relation not in {"co_mentioned_with", "possibly_same_as"}:
            continue
        if row.get("status") != "unverified" or row.get("public_export") is not False:
            errors.append(f"{path.relative_to(KIT_ROOT)}:{lineno} automation co-mention must be unverified and private")
    assert not errors, errors
