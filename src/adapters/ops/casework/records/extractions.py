"""Extraction packet draft and import commands."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from core.casefile import append_jsonl, case_path, ensure_case, log_action, record_path, write_json
from core.lanes.registry import template_records

from .workspace import find_source

DEFAULT_EXTRACTION = {
    "source_id": "",
    "extraction_notes": "",
    "entities": [],
    "places": [],
    "artifacts": [],
    "claims": [],
    "events": [],
    "event_links": [],
    "relationships": [],
    "source_spans": [],
    "quotes": [],
    "redactions": [],
}
TEMPLATE_RECORDS = template_records()
EXTRACTION_TEMPLATE_FILES = {name: row["template_file"] for name, row in TEMPLATE_RECORDS.items()}
EXTRACTION_TEMPLATE_NOTES = {name: row["notes"] for name, row in TEMPLATE_RECORDS.items()}


def fresh_default_extraction() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_EXTRACTION)


def load_extraction_template(template_name: str) -> dict[str, Any]:
    filename = EXTRACTION_TEMPLATE_FILES.get(template_name)
    if not filename:
        raise SystemExit(f"Unknown extraction template: {template_name}")
    data = _load_template_file(filename) or fresh_default_extraction()
    packet = fresh_default_extraction()
    for key, value in data.items():
        packet[key] = value
    for key, value in DEFAULT_EXTRACTION.items():
        if key not in packet:
            packet[key] = [] if isinstance(value, list) else value
    packet["extraction_template"] = template_name
    packet["template_focus"] = EXTRACTION_TEMPLATE_NOTES[template_name]
    return packet


def draft_extraction(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    source = find_source(args.case_dir, args.source_id)
    if not source:
        raise SystemExit(f"Source not found: {args.source_id}")
    packet = load_extraction_template(args.template)
    packet["source_id"] = args.source_id
    packet["source_metadata"] = source
    packet["extraction_instructions"] = (
        "Fill arrays using only claims directly supported by this source. "
        "Treat eyewitness statements as claims. Do not infer guilt, motive, membership, or relationships. "
        "Set claim assertion_type to distinguish source-stated facts, allegations, denials, court findings, "
        "self-reports, biography claims, lead-only items, and expert context. "
        "Add source_spans for page, paragraph, timestamp, exhibit, docket item, accession, or quote-offset locators. "
        "Set public_export=false for living private persons, minors, private addresses/contact info, and weak allegations."
    )
    text_rel = source.get("text_path")
    if text_rel:
        text_path = cdir / text_rel
        packet["source_text_path"] = text_rel
        if text_path.exists():
            packet["source_excerpt_for_orientation"] = text_path.read_text(encoding="utf-8", errors="replace")[
                : args.excerpt_chars
            ]
    out = cdir / "staging" / "extractions" / f"{args.source_id}_extraction.json"
    write_json(out, packet)
    print(f"Wrote draft extraction packet: {out}")


def import_extraction(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    path = Path(args.extraction_json).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"Missing extraction JSON: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    source_id = data.get("source_id")
    if not source_id:
        raise SystemExit("Extraction JSON must include source_id")
    if not find_source(args.case_dir, source_id):
        raise SystemExit(f"Unknown source_id in extraction: {source_id}")
    counts: dict[str, int] = {}
    for key, record_name in _record_mapping().items():
        rows = data.get(key, []) or []
        if not isinstance(rows, list):
            raise SystemExit(f"Expected {key} to be a list")
        for row in rows:
            if not isinstance(row, dict):
                raise SystemExit(f"Expected each item in {key} to be an object")
            row.setdefault("source_ids", [source_id])
            if key in {"quotes", "source_spans"}:
                row.setdefault("source_id", source_id)
            if key == "source_spans" and not row.get("source_span_id") and row.get("span_id"):
                row["source_span_id"] = row["span_id"]
            append_jsonl(record_path(args.case_dir, record_name), row)
        counts[key] = len(rows)
    log_action(args.case_dir, "import_extraction", {"source_id": source_id, "path": str(path), "counts": counts})
    print(json.dumps({"imported": counts}, indent=2))


def _record_mapping() -> dict[str, str]:
    return {
        "entities": "entities",
        "places": "places",
        "artifacts": "artifacts",
        "claims": "claims",
        "events": "events",
        "event_links": "event_links",
        "relationships": "relationships",
        "source_spans": "source_spans",
        "quotes": "quotes",
        "redactions": "redactions",
    }


def _load_template_file(filename: str) -> dict[str, Any] | None:
    for root in [Path.cwd(), *Path(__file__).resolve().parents]:
        for rel in (
            Path(".agents/skills/truecrime-cult-research/assets/templates") / filename,
            Path("tc-c-kit/.agents/skills/truecrime-cult-research/assets/templates") / filename,
        ):
            path = root / rel
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
    return None
