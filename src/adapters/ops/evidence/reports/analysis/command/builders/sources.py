"""Source quality data products for analysis chart exports."""

from __future__ import annotations

from typing import Any

from adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from adapters.ops.evidence.reports.common import parse_cell_list


def build_source_dashboard(ctx: AnalysisContext) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_counter = {sid: _source_counter_row(sid, source) for sid, source in ctx.source_by_id.items()}
    _count_source_records(source_counter, ctx.claims, "claim_count", "source_ids", "claim")
    _count_source_records(source_counter, ctx.events, "event_count", "source_ids")
    _count_source_records(source_counter, ctx.event_links, "event_link_count", "source_ids")
    _count_source_records(source_counter, ctx.relationships, "relationship_count", "source_ids")
    _count_source_records(source_counter, ctx.entities, "entity_count", "source_ids")
    for person in ctx.people:
        for sid in parse_cell_list(person.get("source_ids")):
            if sid in source_counter:
                source_counter[sid]["person_count"] += 1
    source_dashboard = sorted(source_counter.values(), key=lambda row: (str(row["reliability_grade"]), str(row["source_id"])))
    grade_counts: dict[str, int] = {}
    for source in source_dashboard:
        grade = str(source.get("reliability_grade", ""))
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
    grade_rows = [{"grade": grade, "count": count} for grade, count in sorted(grade_counts.items())]
    return source_dashboard, grade_rows


def _source_counter_row(sid: str, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": sid,
        "title": source.get("title", ""),
        "reliability_grade": source.get("reliability_grade", ""),
        "source_type": source.get("source_type", ""),
        "publisher": source.get("publisher", ""),
        "date_published": source.get("date_published", ""),
        "date_accessed": source.get("date_accessed", ""),
        "url": source.get("url", ""),
        "independence_group": source.get("independence_group", ""),
        "claim_count": 0,
        "event_count": 0,
        "event_link_count": 0,
        "relationship_count": 0,
        "entity_count": 0,
        "person_count": 0,
        "verified_claim_count": 0,
        "corroborated_claim_count": 0,
        "single_source_claim_count": 0,
        "disputed_claim_count": 0,
        "unverified_claim_count": 0,
        "needs_privacy_review_count": 0,
        "nonpublic_record_count": 0,
        "source_quality_notes": source.get("notes", ""),
        "public_export": source.get("public_export", True),
    }


def _count_source_records(
    source_counter: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
    count_key: str,
    source_key: str,
    status_kind: str = "",
) -> None:
    for row in rows:
        for sid in parse_cell_list(row.get(source_key)):
            if sid not in source_counter:
                continue
            source_counter[sid][count_key] += 1
            if status_kind == "claim":
                status_key = f"{row.get('status', 'unknown')}_claim_count"
                if status_key in source_counter[sid]:
                    source_counter[sid][status_key] += 1
                if row.get("privacy_review") and row.get("privacy_review") != "clear":
                    source_counter[sid]["needs_privacy_review_count"] += 1
            if row.get("public_export", True) is False:
                source_counter[sid]["nonpublic_record_count"] += 1
