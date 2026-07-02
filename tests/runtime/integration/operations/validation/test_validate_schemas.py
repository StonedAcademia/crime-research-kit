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
