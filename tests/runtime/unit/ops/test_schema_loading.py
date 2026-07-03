"""Schema resolution works from any CWD and without a repo checkout."""

from __future__ import annotations

from pathlib import Path

from crime_research_kit._runtime.adapters.ops.casework.records.validation import SCHEMA_BY_RECORD, _schema_roots, load_schema
from tests.helpers import KIT_ROOT


def test_every_record_schema_resolves(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # far away from the repo checkout
    for record_name, schema_name in SCHEMA_BY_RECORD.items():
        schema = load_schema(schema_name)
        assert schema is not None, f"missing schema for {record_name}"
        assert schema.get("type") == "object"
        assert "required" in schema


def test_unknown_schema_returns_none():
    assert load_schema("nonexistent.schema.json") is None


def test_schema_roots_include_checkout_after_runtime_move():
    assert _schema_roots()[0] == KIT_ROOT / "docs" / "schemas"


def test_packaged_schemas_resolve_without_checkout(monkeypatch):
    """`_schema_roots()` only appends the packaged `crime_research_kit._runtime.core.models` schemas
    root as a fallback; the repo checkout's `docs/schemas` always exists in
    CI, so that fallback branch normally never runs. Force
    `Path.exists()` to report False specifically for the checkout's
    `docs/schemas` directory (every other `Path.exists()` call is left
    untouched) so `_schema_roots()` is forced down to just the packaged
    `crime_research_kit._runtime.core.models` resource root, then confirm every record schema still
    resolves through it. If the packaged fallback in `_schema_roots()`
    were removed, `load_schema` would find no roots left and return None
    for every schema below, failing this test.
    """
    real_exists = Path.exists

    def fake_exists(self: Path) -> bool:
        if self.name == "schemas" and self.parent.name == "docs":
            return False
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)

    for record_name, schema_name in SCHEMA_BY_RECORD.items():
        schema = load_schema(schema_name)
        assert schema is not None, f"missing schema for {record_name}"
        assert "required" in schema
