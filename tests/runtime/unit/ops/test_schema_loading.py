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
