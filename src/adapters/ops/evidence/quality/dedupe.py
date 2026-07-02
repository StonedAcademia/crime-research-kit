"""Duplicate-candidate reporting for case records."""

from __future__ import annotations

import argparse
import json
from typing import Any

from core.casefile import case_path, ensure_case, log_action, now_utc, read_jsonl, record_path, today, write_json

from ..ledger.records import compact_record, normalize_match_text, normalize_url, report_out_path


def append_duplicate_candidate(
    candidates: list[dict[str, Any]],
    *,
    record_type: str,
    reason: str,
    key: str,
    rows: list[tuple[int, dict[str, Any]]],
) -> None:
    if len(rows) >= 2:
        candidates.append(
            {
                "record_type": record_type,
                "reason": reason,
                "match_key": key,
                "records": [compact_record(record_type, row, idx) for idx, row in rows],
            }
        )


def dedupe(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    record_types = ["entities", "sources", "claims"] if getattr(args, "record_type", "all") == "all" else [args.record_type]
    candidates: list[dict[str, Any]] = []
    if "entities" in record_types:
        _append_entity_candidates(candidates, args.case_dir, args.min_key_chars)
    if "sources" in record_types:
        _append_source_candidates(candidates, args.case_dir, args.min_key_chars)
    if "claims" in record_types:
        _append_claim_candidates(candidates, args.case_dir, args.min_key_chars)
    summary: dict[str, int] = {}
    for candidate in candidates:
        kind = str(candidate["record_type"])
        summary[kind] = summary.get(kind, 0) + 1
    report = {
        "generated_at": now_utc(),
        "case_dir": str(case_path(args.case_dir)),
        "policy": "This report does not merge or delete evidence rows.",
        "candidate_count": len(candidates),
        "summary": summary,
        "candidates": candidates,
    }
    out = report_out_path(args.case_dir, getattr(args, "out", None), f"staging/candidates/dedupe_report_{today()}.json")
    write_json(out, report)
    log_action(args.case_dir, "dedupe", {"record_types": record_types, "candidate_count": len(candidates), "summary": summary, "report": str(out)})
    print(json.dumps({"candidate_count": len(candidates), "summary": summary, "report": str(out)}, indent=2, ensure_ascii=False))


def _append_entity_candidates(candidates: list[dict[str, Any]], case_dir: str, min_key_chars: int) -> None:
    groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for idx, entity in enumerate(read_jsonl(record_path(case_dir, "entities")), start=1):
        values = [entity.get("name"), entity.get("display_name"), *(entity.get("aliases", []) or [])]
        for value in values:
            key = normalize_match_text(value)
            if len(key) >= min_key_chars:
                groups.setdefault(key, []).append((idx, entity))
    for key, rows in sorted(groups.items()):
        append_duplicate_candidate(candidates, record_type="entities", reason="same_normalized_name_or_alias", key=key, rows=rows)


def _append_source_candidates(candidates: list[dict[str, Any]], case_dir: str, min_key_chars: int) -> None:
    groups: dict[tuple[str, str], list[tuple[int, dict[str, Any]]]] = {}
    for idx, source in enumerate(read_jsonl(record_path(case_dir, "sources")), start=1):
        for field in ("url", "archive_url"):
            key = normalize_url(source.get(field))
            if key:
                groups.setdefault((f"same_{field}", key), []).append((idx, source))
        title_key = normalize_match_text(source.get("title"))
        publisher_key = normalize_match_text(source.get("publisher"))
        date_key = normalize_match_text(source.get("date_published"))
        if len(title_key) >= min_key_chars:
            groups.setdefault(("same_title_publisher_date", "|".join([title_key, publisher_key, date_key])), []).append((idx, source))
        for field in ("raw_path", "text_path"):
            key = str(source.get(field) or "").strip()
            if key:
                groups.setdefault((f"same_{field}", key), []).append((idx, source))
    for (reason, key), rows in sorted(groups.items()):
        append_duplicate_candidate(candidates, record_type="sources", reason=reason, key=key, rows=rows)


def _append_claim_candidates(candidates: list[dict[str, Any]], case_dir: str, min_key_chars: int) -> None:
    groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for idx, claim in enumerate(read_jsonl(record_path(case_dir, "claims")), start=1):
        key = normalize_match_text(claim.get("claim"))
        if len(key) >= min_key_chars:
            groups.setdefault(key, []).append((idx, claim))
    for key, rows in sorted(groups.items()):
        append_duplicate_candidate(candidates, record_type="claims", reason="same_normalized_claim_text", key=key, rows=rows)
