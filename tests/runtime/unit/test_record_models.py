"""Record models parse real ledger rows and reject schema violations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.casefile import RECORD_FILES
from core.models.records import MODEL_BY_RECORD, ClaimRecord

SYNTHETIC_RECORDS = Path(__file__).resolve().parents[3] / "data" / "examples" / "synthetic_case" / "records"


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
