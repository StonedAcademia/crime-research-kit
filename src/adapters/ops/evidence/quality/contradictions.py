"""Claim contradiction audit reporting."""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from typing import Any

from core.casefile import case_path, ensure_case, log_action, now_utc, read_jsonl, record_path, stable_id, write_json

from ...casework.records.names.matching import clean_id_list
from ..shared.records import compact_record, normalize_match_text, public_rows, report_out_path


def claim_tokens(claim: dict[str, Any]) -> set[str]:
    text = normalize_match_text(claim.get("claim"))
    return {token for token in text.split() if len(token) > 3}


def claim_overlap(left: dict[str, Any], right: dict[str, Any]) -> float:
    left_tokens = claim_tokens(left)
    right_tokens = claim_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def contradiction_severity(flag_type: str, left: dict[str, Any], right: dict[str, Any]) -> str:
    assertion_types = {str(left.get("assertion_type", "")), str(right.get("assertion_type", ""))}
    statuses = {str(left.get("status", "")), str(right.get("status", ""))}
    if "court_finding" in assertion_types or "false_or_retracted" in statuses:
        return "high"
    if flag_type in {"explicit_contradiction", "opposing_assertion_types"}:
        return "medium"
    return "low"


def make_contradiction_flag(
    *,
    flag_type: str,
    left: dict[str, Any],
    right: dict[str, Any],
    reason: str,
    overlap: float | None = None,
) -> dict[str, Any]:
    left_id = str(left.get("claim_id", ""))
    right_id = str(right.get("claim_id", ""))
    return {
        "flag_id": stable_id("CF", flag_type, left_id, right_id),
        "flag_type": flag_type,
        "severity": contradiction_severity(flag_type, left, right),
        "claim_ids": sorted([left_id, right_id]),
        "source_ids": sorted(set(clean_id_list(left.get("source_ids"))) | set(clean_id_list(right.get("source_ids")))),
        "assertion_types": sorted({str(left.get("assertion_type", "")), str(right.get("assertion_type", ""))}),
        "statuses": sorted({str(left.get("status", "")), str(right.get("status", ""))}),
        "text_overlap": overlap,
        "reason": reason,
        "records": [compact_record("claims", left), compact_record("claims", right)],
    }


def audit_contradictions(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    claims = read_jsonl(record_path(args.case_dir, "claims"))
    if not getattr(args, "include_private", False):
        claims = public_rows(claims)
    flags = _flags(claims, args.min_overlap)
    summary: dict[str, int] = {}
    for flag in flags:
        summary[str(flag["flag_type"])] = summary.get(str(flag["flag_type"]), 0) + 1
    report = {
        "generated_at": now_utc(),
        "case_dir": str(case_path(args.case_dir)),
        "include_private": getattr(args, "include_private", False),
        "flag_count": len(flags),
        "summary": summary,
        "flags": flags,
        "policy": "This report identifies review targets; it does not change claim status or confidence.",
    }
    out = report_out_path(args.case_dir, getattr(args, "out", None), "exports/claim_contradiction_audit.json")
    write_json(out, report)
    log_action(args.case_dir, "audit_contradictions", {"flag_count": len(flags), "summary": summary, "report": str(out), "include_private": getattr(args, "include_private", False)})
    print(json.dumps({"flag_count": len(flags), "summary": summary, "report": str(out)}, indent=2, ensure_ascii=False))
    if getattr(args, "fail_on_flags", False) and flags:
        raise SystemExit(1)


def _flags(claims: list[dict[str, Any]], min_overlap: float) -> list[dict[str, Any]]:
    claim_by_id = {str(claim.get("claim_id")): claim for claim in claims if claim.get("claim_id")}
    flags: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str, str]] = set()
    for claim in claims:
        for other_id in clean_id_list(claim.get("contradicts")):
            other = claim_by_id.get(other_id)
            if other:
                _add_flag(flags, seen_pairs, make_contradiction_flag(flag_type="explicit_contradiction", left=claim, right=other, reason="A claim explicitly lists the other claim in its contradicts array."))
    for left, right in combinations(claims, 2):
        left_id = str(left.get("claim_id", ""))
        right_id = str(right.get("claim_id", ""))
        if not left_id or not right_id:
            continue
        overlap = claim_overlap(left, right)
        if overlap >= min_overlap:
            _add_similarity_flags(flags, seen_pairs, left, right, overlap)
    return flags


def _add_similarity_flags(flags: list[dict[str, Any]], seen_pairs: set[tuple[str, str, str]], left: dict[str, Any], right: dict[str, Any], overlap: float) -> None:
    assertion_types = {str(left.get("assertion_type", "")), str(right.get("assertion_type", ""))}
    statuses = {str(left.get("status", "")), str(right.get("status", ""))}
    if {"allegation", "denial"} <= assertion_types:
        _add_flag(flags, seen_pairs, make_contradiction_flag(flag_type="opposing_assertion_types", left=left, right=right, overlap=overlap, reason="Similar claim text has allegation and denial assertion types."))
    if "court_finding" in assertion_types and ("allegation" in assertion_types or "denial" in assertion_types):
        _add_flag(flags, seen_pairs, make_contradiction_flag(flag_type="court_finding_conflict_review", left=left, right=right, overlap=overlap, reason="Similar claim text includes a court finding and a claim framed differently by another source."))
    if "false_or_retracted" in statuses and statuses & {"verified", "corroborated", "single_source"}:
        _add_flag(flags, seen_pairs, make_contradiction_flag(flag_type="status_conflict", left=left, right=right, overlap=overlap, reason="Similar claim text has false/retracted status alongside an active support status."))


def _add_flag(flags: list[dict[str, Any]], seen_pairs: set[tuple[str, str, str]], flag: dict[str, Any]) -> None:
    ids = tuple(sorted(flag["claim_ids"]))
    key = (flag["flag_type"], ids[0], ids[1])
    if key not in seen_pairs:
        seen_pairs.add(key)
        flags.append(flag)
