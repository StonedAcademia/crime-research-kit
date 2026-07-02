"""Governance: pydantic record models stay aligned with the canonical schemas."""

from __future__ import annotations

import json
import types
import typing
from pathlib import Path

import pytest

from adapters.ops.casework.records.validation import SCHEMA_BY_RECORD, load_schema
from core.models.records import MODEL_BY_RECORD
from tests.helpers import KIT_ROOT


def test_schemas_parse():
    schema_paths = [
        *(KIT_ROOT / "docs" / "schemas").rglob("*.schema.json"),
        *(KIT_ROOT / "docs" / "registry").glob("*.schema.json"),
    ]
    for path in schema_paths:
        json.loads(path.read_text())


def test_skill_exists():
    assert (KIT_ROOT / ".agents/skills/truecrime-cult-research/SKILL.md").exists()


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
