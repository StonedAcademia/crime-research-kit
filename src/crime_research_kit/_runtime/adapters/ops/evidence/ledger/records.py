"""Shared record and public-output helpers for evidence commands."""

from __future__ import annotations

import csv
import re
import urllib.parse
from pathlib import Path
from typing import Any, Iterable

from crime_research_kit._runtime.core.casefile import case_path

ID_FIELDS = {
    "sources": "source_id",
    "entities": "entity_id",
    "places": "place_id",
    "artifacts": "artifact_id",
    "claims": "claim_id",
    "events": "event_id",
    "event_links": "event_link_id",
    "relationships": "rel_id",
    "source_spans": "source_span_id",
    "quotes": "quote_id",
    "research_actions": "timestamp",
    "redactions": "redaction_id",
}


def flatten(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ";".join(str(v) for v in value)
    return str(value)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: flatten(row.get(column)) for column in columns})


def public_rows(rows: Iterable[dict[str, Any]], include_private: bool = False) -> list[dict[str, Any]]:
    if include_private:
        return list(rows)
    return [row for row in rows if row.get("public_export", True) is not False]


def discover_cases(cases_root: str | Path) -> list[Path]:
    root = Path(cases_root).expanduser().resolve()
    if (root / "case.json").exists():
        return [root]
    if not root.exists():
        raise SystemExit(f"Missing cases root: {root}")
    cases = sorted(path.parent for path in root.glob("*/case.json"))
    if not cases:
        raise SystemExit(f"No case workspaces found under: {root}")
    return cases


def source_independence_key(source: dict[str, Any]) -> str:
    if source.get("independence_group"):
        return str(source["independence_group"])
    if source.get("publisher"):
        return str(source["publisher"])
    if source.get("url"):
        parsed = urllib.parse.urlparse(str(source["url"]))
        if parsed.netloc:
            return parsed.netloc.lower()
    return str(source.get("source_id", "unknown"))


def record_id(record_name: str, row: dict[str, Any], idx: int = 0) -> str:
    field = ID_FIELDS.get(record_name)
    if field and row.get(field) not in (None, ""):
        return str(row[field])
    return f"{record_name}:{idx}"


def normalize_match_text(value: Any) -> str:
    text = str(value or "").casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urllib.parse.urlparse(raw)
    if not parsed.netloc:
        return normalize_match_text(raw)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = re.sub(r"/+$", "", parsed.path or "/")
    query = urllib.parse.urlencode(
        sorted(
            (key, val)
            for key, val in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
        )
    )
    return urllib.parse.urlunparse((parsed.scheme.lower() or "https", netloc, path, "", query, ""))


def report_out_path(case_dir: str | Path, requested: str | None, default_rel: str) -> Path:
    if requested:
        return Path(requested).expanduser().resolve()
    return case_path(case_dir) / default_rel


def compact_record(record_name: str, row: dict[str, Any], idx: int = 0) -> dict[str, Any]:
    item = {"record_type": record_name, "record_id": record_id(record_name, row, idx)}
    for field in _compact_fields():
        if row.get(field) not in (None, "", []):
            item[field] = row.get(field)
    return item


def _compact_fields() -> tuple[str, ...]:
    return (
        "source_id",
        "entity_id",
        "claim_id",
        "event_id",
        "event_link_id",
        "rel_id",
        "source_span_id",
        "span_id",
        "title",
        "name",
        "display_name",
        "claim",
        "publisher",
        "url",
        "status",
        "source_ids",
        "public_export",
    )
