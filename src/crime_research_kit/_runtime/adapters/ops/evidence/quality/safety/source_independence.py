"""Source-independence audit command."""

from __future__ import annotations

import argparse
import json
from typing import Any, Iterable

from crime_research_kit._runtime.core.casefile import RECORD_FILES, case_path, ensure_case, log_action, now_utc, read_jsonl, record_path, write_json

from crime_research_kit._runtime.adapters.ops.casework.records.names.matching import clean_id_list
from crime_research_kit._runtime.adapters.ops.evidence.quality.safety.public_export import source_rows_for_ids
from crime_research_kit._runtime.adapters.ops.evidence.ledger.records import (
    normalize_match_text,
    public_rows,
    record_id,
    report_out_path,
    source_independence_key,
)

WIRE_TERMS = {"associated press", "ap", "reuters", "upi", "united press international", "afp"}
PRESS_RELEASE_TERMS = {
    "press release",
    "news release",
    "pr newswire",
    "business wire",
    "globenewswire",
    "marketwired",
    "official statement",
}


def source_text_blob(source: dict[str, Any]) -> str:
    return " ".join(str(source.get(field, "")) for field in ("title", "source_type", "author", "publisher", "notes")).casefold()


def is_wire_source(source: dict[str, Any]) -> bool:
    text = source_text_blob(source)
    if "associated press" in text or "reuters" in text or "united press international" in text or "afp" in text:
        return True
    return any(str(source.get(field, "")).strip().casefold() == "ap" for field in ("author", "publisher"))


def is_press_release_source(source: dict[str, Any]) -> bool:
    text = source_text_blob(source)
    return any(term in text for term in PRESS_RELEASE_TERMS)


def add_source_independence_flag(
    flags: list[dict[str, Any]],
    *,
    flag_type: str,
    message: str,
    source_ids: Iterable[str],
    record_type: str = "",
    record_id_value: str = "",
    independence_groups: Iterable[str] = (),
) -> None:
    normalized_source_ids = sorted(set(str(source_id) for source_id in source_ids if source_id))
    flags.append(
        {
            "flag_type": flag_type,
            "record_type": record_type,
            "record_id": record_id_value,
            "source_ids": normalized_source_ids,
            "source_ids_joined": ";".join(normalized_source_ids),
            "independence_groups": sorted(set(str(group) for group in independence_groups if group)),
            "message": message,
        }
    )


def source_independence(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    sources = read_jsonl(record_path(args.case_dir, "sources"))
    source_by_id = {str(source.get("source_id")): source for source in sources if source.get("source_id")}
    flags: list[dict[str, Any]] = []
    _repeated_title_flags(flags, sources, getattr(args, "min_title_chars", 16))
    _record_support_flags(flags, args, source_by_id)
    summary: dict[str, int] = {}
    for flag in flags:
        key = str(flag["flag_type"])
        summary[key] = summary.get(key, 0) + 1
    report = {
        "generated_at": now_utc(),
        "case_dir": str(cdir),
        "include_private": getattr(args, "include_private", False),
        "flag_count": len(flags),
        "summary": summary,
        "flags": flags,
    }
    out = report_out_path(args.case_dir, getattr(args, "out", None), "exports/source_independence_report.json")
    write_json(out, report)
    log_action(args.case_dir, "audit_source_independence", {"flag_count": len(flags), "summary": summary, "report": str(out), "include_private": getattr(args, "include_private", False)})
    print(json.dumps({"flag_count": len(flags), "summary": summary, "report": str(out)}, indent=2, ensure_ascii=False))
    if getattr(args, "fail_on_flags", False) and flags:
        raise SystemExit(1)


def _repeated_title_flags(flags: list[dict[str, Any]], sources: list[dict[str, Any]], min_title_chars: int) -> None:
    title_groups: dict[str, list[dict[str, Any]]] = {}
    for source in sources:
        key = normalize_match_text(source.get("title"))
        if len(key) >= min_title_chars:
            title_groups.setdefault(key, []).append(source)
    for group_sources in title_groups.values():
        if len(group_sources) < 2:
            continue
        source_ids = [str(source.get("source_id", "")) for source in group_sources]
        groups = [source_independence_key(source) for source in group_sources]
        if any(is_wire_source(source) for source in group_sources):
            add_source_independence_flag(flags, flag_type="repeated_wire_copy", message="Multiple sources share a title and at least one appears to be wire copy.", source_ids=source_ids, independence_groups=groups)
        if any(is_press_release_source(source) for source in group_sources):
            add_source_independence_flag(flags, flag_type="press_release_repetition", message="Multiple sources share a title and at least one appears to be a press release or release repost.", source_ids=source_ids, independence_groups=groups)


def _record_support_flags(
    flags: list[dict[str, Any]],
    args: argparse.Namespace,
    source_by_id: dict[str, dict[str, Any]],
) -> None:
    record_names = [name for name in ("claims", "events", "event_links", "relationships") if name in RECORD_FILES]
    for record_name in record_names:
        rows = read_jsonl(record_path(args.case_dir, record_name))
        if not getattr(args, "include_private", False):
            rows = public_rows(rows)
        for idx, row in enumerate(rows, start=1):
            source_ids = clean_id_list(row.get("source_ids"))
            if source_ids:
                _record_source_flags(flags, record_name, row, idx, source_by_id, source_ids)


def _record_source_flags(
    flags: list[dict[str, Any]],
    record_name: str,
    row: dict[str, Any],
    idx: int,
    source_by_id: dict[str, dict[str, Any]],
    source_ids: list[str],
) -> None:
    source_rows, _missing = source_rows_for_ids(source_by_id, source_ids)
    if not source_rows:
        return
    groups = [source_independence_key(source) for source in source_rows]
    rid = record_id(record_name, row, idx)
    if len(source_rows) > 1 and len(set(groups)) <= 1:
        add_source_independence_flag(flags, flag_type="same_source_chain", message="Record cites multiple sources that collapse to the same independence group.", source_ids=source_ids, record_type=record_name, record_id_value=rid, independence_groups=groups)
    if source_rows and all(is_wire_source(source) for source in source_rows):
        add_source_independence_flag(flags, flag_type="wire_copy_support_only", message="Record support appears to come only from wire-copy sources.", source_ids=source_ids, record_type=record_name, record_id_value=rid, independence_groups=groups)
    if source_rows and all(is_press_release_source(source) for source in source_rows):
        add_source_independence_flag(flags, flag_type="press_release_support_only", message="Record support appears to come only from press-release or release-repost sources.", source_ids=source_ids, record_type=record_name, record_id_value=rid, independence_groups=groups)
