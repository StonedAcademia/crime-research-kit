"""Source preservation checks and metadata updates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from crime_research_kit._runtime.core.casefile import (
    ensure_case,
    file_sha256,
    log_action,
    now_utc,
    read_jsonl,
    record_path,
    resolve_case_path,
    write_json,
    write_jsonl,
)

from ..ledger.records import report_out_path


def preservation_artifact(case_dir: str | Path, source: dict[str, Any], path_field: str) -> dict[str, Any]:
    rel_value = source.get(path_field)
    artifact = {"field": path_field, "path": rel_value, "exists": False, "size_bytes": None, "sha256": None, "issue": None}
    path = resolve_case_path(case_dir, str(rel_value)) if rel_value else None
    if not path:
        artifact["issue"] = f"{path_field} is not set"
        return artifact
    if not path.exists():
        artifact["issue"] = f"{path_field} does not exist on disk"
        return artifact
    if not path.is_file():
        artifact["issue"] = f"{path_field} is not a file"
        return artifact
    artifact.update({"exists": True, "size_bytes": path.stat().st_size, "sha256": file_sha256(path)})
    return artifact


def source_preservation_report(case_dir: str | Path, source: dict[str, Any]) -> dict[str, Any]:
    artifacts = [preservation_artifact(case_dir, source, "raw_path"), preservation_artifact(case_dir, source, "text_path")]
    existing_artifacts = [item for item in artifacts if item["exists"]]
    configured_missing = [item for item in artifacts if item.get("path") and not item["exists"]]
    if configured_missing:
        status = "missing_artifacts"
    elif existing_artifacts:
        status = "captured"
    elif source.get("archive_url"):
        status = "registered_with_archive"
    else:
        status = "metadata_only"
    return {
        "generated_at": now_utc(),
        "source_id": source.get("source_id"),
        "title": source.get("title"),
        "url": source.get("url"),
        "archive_url": source.get("archive_url"),
        "content_type": source.get("content_type"),
        "capture_method": source.get("capture_method"),
        "capture_timestamp": source.get("capture_timestamp"),
        "preservation_status": status,
        "artifacts": artifacts,
        "warnings": [str(item["issue"]) for item in artifacts if item.get("issue")],
    }


def preserve_source(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    sources = read_jsonl(record_path(args.case_dir, "sources"))
    source = next((row for row in sources if row.get("source_id") == args.source_id), None)
    if not source:
        raise SystemExit(f"Source not found: {args.source_id}")
    if args.archive_url:
        source["archive_url"] = args.archive_url
    if args.content_type:
        source["content_type"] = args.content_type
    source.setdefault("capture_method", "registered_source")
    source["preservation_checked_at"] = now_utc()
    report = source_preservation_report(args.case_dir, source)
    _apply_report(source, report)
    write_jsonl(record_path(args.case_dir, "sources"), sources)
    out = report_out_path(args.case_dir, getattr(args, "out", None), f"exports/source_preservation/{args.source_id}.json")
    write_json(out, report)
    log_action(
        args.case_dir,
        "preserve_source",
        {"source_id": args.source_id, "report": str(out), "preservation_status": report["preservation_status"], "warnings": report["warnings"]},
    )
    print(json.dumps({"source_id": args.source_id, "preservation_status": report["preservation_status"], "report": str(out)}, indent=2, ensure_ascii=False))


def _apply_report(source: dict[str, Any], report: dict[str, Any]) -> None:
    source["preservation_status"] = report["preservation_status"]
    for artifact in report["artifacts"]:
        if artifact["field"] == "raw_path" and artifact.get("sha256"):
            source["raw_sha256"] = artifact["sha256"]
            source["raw_size_bytes"] = artifact["size_bytes"]
        if artifact["field"] == "text_path" and artifact.get("sha256"):
            source["text_sha256"] = artifact["sha256"]
            source["text_size_bytes"] = artifact["size_bytes"]
    source["preservation_warnings"] = report["warnings"]
