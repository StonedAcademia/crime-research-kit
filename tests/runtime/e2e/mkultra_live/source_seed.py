from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from crime_research_kit._runtime.core.casefile import append_jsonl, file_sha256, now_utc, read_jsonl, record_path, today
from tests.helpers import KIT_ROOT

MANIFEST_PATH = KIT_ROOT / "docs" / "guides" / "courses" / "samples" / "mkultra" / "sources" / "manifest.json"
CURATED_SOURCE_IDS = (
    "S_NSARCHIVE_MKULTRA_CONTEXT_2024",
    "S_CIA_MKULTRA_IG_1963",
    "S_FBI_FINDERS_PART_01",
    "S_FBI_JONESTOWN_HISTORY",
)
PRIMARY_SOURCE_ID = "S_NSARCHIVE_MKULTRA_CONTEXT_2024"


def manifest_sources() -> dict[str, dict[str, Any]]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {str(row["source_id"]): row for row in data["sources"]}


def register_curated_sources(case_dir: Path) -> None:
    sources_by_id = manifest_sources()
    existing = {row.get("source_id") for row in read_jsonl(record_path(case_dir, "sources"))}
    for source_id in CURATED_SOURCE_IDS:
        if source_id in existing:
            continue
        row = sources_by_id[source_id]
        raw_rel = str(row["raw_path"] or f"raw/downloads/{source_id}")
        raw_path = case_dir / raw_rel
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        response = httpx.get(str(row["url"]), follow_redirects=True, timeout=60)
        if not response.is_success:
            _append_source(case_dir, _metadata_only_record(row, response.status_code))
            continue
        raw_path.write_bytes(response.content)
        content_type = response.headers.get("content-type", "")
        text_rel, text_sha = _write_text(case_dir, row, raw_rel, response.content, content_type)
        _append_source(case_dir, _captured_record(row, raw_rel, text_rel, text_sha, content_type, raw_path))


def _append_source(case_dir: Path, record: dict[str, Any]) -> None:
    append_jsonl(record_path(case_dir, "sources"), record)


def _captured_record(
    row: dict[str, Any],
    raw_rel: str,
    text_rel: str | None,
    text_sha: str | None,
    content_type: str,
    raw_path: Path,
) -> dict[str, Any]:
    return {
        **_base_record(row),
        "raw_path": raw_rel,
        "text_path": text_rel,
        "content_type": content_type or None,
        "capture_method": "ingest_url",
        "raw_sha256": file_sha256(raw_path),
        "text_sha256": text_sha,
        "preservation_status": "captured",
        "preservation_warnings": [],
        "notes": "Live MKULTRA E2E capture from tracked course manifest.",
    }


def _metadata_only_record(row: dict[str, Any], status_code: int) -> dict[str, Any]:
    return {
        **_base_record(row),
        "raw_path": None,
        "text_path": None,
        "content_type": None,
        "capture_method": "manual_registration",
        "raw_sha256": None,
        "text_sha256": None,
        "preservation_status": "metadata_only",
        "preservation_warnings": [f"live capture returned HTTP {status_code}"],
        "notes": f"Live MKULTRA E2E registered metadata only; source returned HTTP {status_code}.",
    }


def _base_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": row["source_id"],
        "title": row["title"],
        "source_type": row["source_type"],
        "author": None,
        "publisher": row.get("publisher"),
        "date_published": row.get("date_published"),
        "date_accessed": today(),
        "url": row.get("url"),
        "archive_url": None,
        "capture_timestamp": now_utc(),
        "reliability_grade": row["reliability_grade"],
        "independence_group": row.get("publisher"),
        "public_export": True,
    }


def _write_text(
    case_dir: Path,
    row: dict[str, Any],
    raw_rel: str,
    raw: bytes,
    content_type: str,
) -> tuple[str | None, str | None]:
    text_rel = row.get("text_path") if _is_textual(raw_rel, content_type) else None
    if not text_rel:
        return None, None
    text_path = case_dir / str(text_rel)
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text(_extract_text(raw, content_type), encoding="utf-8")
    return str(text_rel), file_sha256(text_path)


def _is_textual(raw_rel: str, content_type: str) -> bool:
    lowered = raw_rel.lower()
    return lowered.endswith((".html", ".htm", ".txt")) or "html" in content_type or content_type.startswith("text/")


def _extract_text(raw: bytes, content_type: str) -> str:
    from crime_research_kit._runtime.adapters.ops.casework.records.intake.web import extract_html_text

    if "html" in content_type:
        text, _meta = extract_html_text(raw, content_type)
        return text
    return raw.decode("utf-8", errors="replace")
