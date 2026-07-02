"""Shared evidence scoring and sort helpers."""

from __future__ import annotations

import re
from typing import Any

from adapters.ops.evidence.shared.records import source_independence_key


def evidence_level(claim: dict[str, Any], source_rows: list[dict[str, Any]]) -> str:
    status = str(claim.get("status", "unknown"))
    public = claim.get("public_export", True) is not False
    source_count = len(source_rows)
    independent_count = len({source_independence_key(src) for src in source_rows})
    grades = {str(src.get("reliability_grade", "")) for src in source_rows}

    if status == "false_or_retracted":
        return "false_or_retracted"
    if status == "disputed":
        return "disputed"
    if status == "excluded_from_public_script" or not public:
        return "excluded_from_public"
    if status == "unverified":
        return "unverified"
    if status == "verified":
        return "verified"
    if status == "corroborated":
        return "corroborated"
    if independent_count >= 2:
        return "multi_source"
    if source_count == 1 and "A" in grades:
        return "single_source_grade_a"
    if source_count == 1:
        return "single_source"
    return "no_source"


def grade_summary(source_rows: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for source in source_rows:
        grade = str(source.get("reliability_grade", "") or "unknown")
        counts[grade] = counts.get(grade, 0) + 1
    return ";".join(f"{grade}:{counts[grade]}" for grade in sorted(counts))


def date_sort_key(value: Any) -> tuple[int, int, int, str]:
    raw = str(value or "")
    match = re.match(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", raw)
    if match:
        year = int(match.group(1))
        month = int(match.group(2) or "1")
        day = int(match.group(3) or "1")
        return (year, month, day, raw)
    decade = re.match(r"^(\d{3})0s$", raw)
    if decade:
        return (int(decade.group(1) + "0"), 1, 1, raw)
    return (9999, 12, 31, raw)
