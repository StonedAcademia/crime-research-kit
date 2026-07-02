"""Validation for canonical CRK case records."""

from __future__ import annotations

import argparse
import json
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

import jsonschema

from core.casefile import RECORD_FILES, case_path, ensure_case, read_jsonl, record_path

try:
    from importlib.resources.abc import Traversable
except ImportError:  # Python 3.10 exposes Traversable from importlib.abc.
    from importlib.abc import Traversable

SCHEMA_BY_RECORD = {
    "sources": "source.schema.json",
    "entities": "entity.schema.json",
    "places": "place.schema.json",
    "artifacts": "artifact.schema.json",
    "claims": "claim.schema.json",
    "events": "event.schema.json",
    "event_links": "event_link.schema.json",
    "relationships": "relationship.schema.json",
    "source_spans": "source_span.schema.json",
    "quotes": "quote.schema.json",
    "research_actions": "research_action.schema.json",
    "redactions": "redaction.schema.json",
}


_SCHEMA_GROUPS = ("case", "evidence", "review")


def _schema_roots() -> list[Path | Traversable]:
    checkout = Path(__file__).resolve().parents[5] / "docs" / "schemas"
    roots: list[Path | Traversable] = []
    if checkout.exists():
        roots.append(checkout)
    roots.append(files("core.models").joinpath("schemas_data"))
    return roots


def load_schema(schema_name: str) -> dict[str, Any] | None:
    for root in _schema_roots():
        for group in _SCHEMA_GROUPS:
            candidate = root.joinpath(group).joinpath(schema_name)
            if candidate.is_file():
                return json.loads(candidate.read_text(encoding="utf-8"))
    return None


def _row_errors(
    record_name: str, validator: jsonschema.Draft202012Validator, row: dict[str, Any], idx: int
) -> list[str]:
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
        validator = jsonschema.Draft202012Validator(schema)
        for idx, row in enumerate(rows, start=1):
            errors.extend(_row_errors(record_name, validator, row, idx))
    return errors


def validate(args: argparse.Namespace) -> None:
    errors = validate_case(args.case_dir)
    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Validation passed for {case_path(args.case_dir)}")
