"""Validation for canonical CRK case records."""

from __future__ import annotations

import argparse
import json
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

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


def required_errors(record_name: str, row: dict[str, Any], idx: int) -> list[str]:
    required = {
        "sources": ["source_id", "title", "source_type", "reliability_grade", "date_accessed"],
        "entities": ["entity_id", "entity_type", "name", "status", "source_ids"],
        "places": ["place_id", "name", "source_ids"],
        "artifacts": ["artifact_id", "artifact_type", "name", "source_ids"],
        "claims": ["claim_id", "claim", "status", "confidence", "source_ids"],
        "events": ["event_id", "title", "event_type", "source_ids"],
        "event_links": ["event_link_id", "entity_id", "event_id", "relation_type", "source_ids"],
        "relationships": ["rel_id", "src_entity_id", "dst_entity_id", "relation_type", "source_ids"],
        "source_spans": ["source_span_id", "source_id", "locator_type", "locator"],
        "quotes": ["quote_id", "source_id", "exact_quote"],
        "research_actions": ["timestamp", "action", "details"],
        "redactions": ["redaction_id", "record_id", "reason"],
    }.get(record_name, [])
    return [
        f"{record_name}[{idx}] missing required field: {field}"
        for field in required
        if field not in row or row.get(field) in (None, "")
    ]


def validate_case(case_dir: str | Path) -> list[str]:
    ensure_case(case_dir)
    errors: list[str] = []
    try:
        import jsonschema  # type: ignore
    except Exception:
        jsonschema = None

    for record_name in RECORD_FILES:
        rows = read_jsonl(record_path(case_dir, record_name))
        schema_name = SCHEMA_BY_RECORD.get(record_name, "")
        schema = load_schema(schema_name) if schema_name else None
        for idx, row in enumerate(rows, start=1):
            errors.extend(required_errors(record_name, row, idx))
            if jsonschema and schema:
                try:
                    jsonschema.validate(instance=row, schema=schema)
                except Exception as exc:
                    errors.append(f"{record_name}[{idx}] schema error: {exc}")
    return errors


def validate(args: argparse.Namespace) -> None:
    errors = validate_case(args.case_dir)
    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Validation passed for {case_path(args.case_dir)}")
