"""Case workspace and source-record commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from core.casefile import (
    RECORD_FILES,
    append_jsonl,
    case_path,
    log_action,
    now_utc,
    read_jsonl,
    record_path,
    slugify,
    stable_id,
    today,
    write_json,
)


def load_sources(case_dir: str | Path) -> list[dict[str, Any]]:
    return read_jsonl(record_path(case_dir, "sources"))


def find_source(case_dir: str | Path, source_id: str) -> dict[str, Any] | None:
    for source in load_sources(case_dir):
        if source.get("source_id") == source_id:
            return source
    return None


def init_case(args: argparse.Namespace) -> None:
    cdir = case_path(args.case_dir)
    cdir.mkdir(parents=True, exist_ok=True)
    for subdir in (
        "raw/downloads",
        "raw/sources",
        "records",
        "staging/extractions",
        "staging/candidates",
        "exports/manim",
        "notes",
    ):
        (cdir / subdir).mkdir(parents=True, exist_ok=True)
    case_meta = {
        "case_id": slugify(args.title or cdir.name),
        "title": args.title or cdir.name,
        "created_at": now_utc(),
        "research_scope": args.scope or "",
        "public_interest": args.public_interest or "educational/documentary research",
    }
    write_json(cdir / "case.json", case_meta)
    for filename in RECORD_FILES.values():
        (cdir / "records" / filename).touch(exist_ok=True)
    (cdir / "notes" / "case_brief.md").write_text(f"# Case brief: {case_meta['title']}\n\n", encoding="utf-8")
    print(f"Initialized case workspace: {cdir}")


def add_source_record(
    case_dir: str | Path,
    *,
    title: str,
    source_type: str,
    reliability_grade: str,
    url: str | None = None,
    author: str | None = None,
    publisher: str | None = None,
    date_published: str | None = None,
    archive_url: str | None = None,
    raw_path: str | None = None,
    text_path: str | None = None,
    content_type: str | None = None,
    capture_method: str | None = None,
    capture_timestamp: str | None = None,
    raw_sha256: str | None = None,
    text_sha256: str | None = None,
    preservation_status: str | None = None,
    notes: str = "",
    public_export: bool = True,
) -> dict[str, Any]:
    source_id = stable_id("S", url or title, date_published or "", publisher or "")
    existing = find_source(case_dir, source_id)
    if existing:
        return existing
    record = {
        "source_id": source_id,
        "title": title or "Untitled source",
        "source_type": source_type,
        "author": author,
        "publisher": publisher,
        "date_published": date_published,
        "date_accessed": today(),
        "url": url,
        "archive_url": archive_url,
        "raw_path": raw_path,
        "text_path": text_path,
        "content_type": content_type,
        "capture_method": capture_method,
        "capture_timestamp": capture_timestamp,
        "raw_sha256": raw_sha256,
        "text_sha256": text_sha256,
        "preservation_status": preservation_status,
        "reliability_grade": reliability_grade,
        "independence_group": None,
        "notes": notes,
        "public_export": public_export,
    }
    append_jsonl(record_path(case_dir, "sources"), record)
    log_action(case_dir, "add_source", {"source_id": source_id, "title": title, "url": url})
    return record


def add_source(args: argparse.Namespace) -> None:
    record = add_source_record(
        args.case_dir,
        title=args.title,
        source_type=args.source_type,
        reliability_grade=args.reliability_grade,
        url=args.url,
        author=args.author,
        publisher=args.publisher,
        date_published=args.date_published,
        archive_url=args.archive_url,
        notes=args.notes or "",
        public_export=not args.no_public_export,
    )
    print(json.dumps(record, indent=2, ensure_ascii=False))
