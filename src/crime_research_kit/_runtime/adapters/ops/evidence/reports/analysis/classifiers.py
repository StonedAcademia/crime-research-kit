"""Analysis scoring and readiness classifiers."""

from __future__ import annotations

from typing import Any

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.vocabulary import VocabPacks, load_default_packs
from crime_research_kit._runtime.adapters.ops.evidence.reports.common import parse_cell_list


def status_score(status: str, packs: VocabPacks | None = None) -> float:
    return (packs or load_default_packs()).status_scores.get(status, 0.0)


def source_grade_score(source_rows: list[dict[str, Any]], packs: VocabPacks | None = None) -> float:
    if not source_rows:
        return 0.0
    scores = (packs or load_default_packs()).grade_scores
    return round(max(scores.get(str(source.get("reliability_grade", "")), 0.35) for source in source_rows), 3)


def readiness_label(row: dict[str, Any], source_rows: list[dict[str, Any]] | None = None) -> str:
    status = str(row.get("status", ""))
    privacy = str(row.get("privacy_review", "clear"))
    public_export = row.get("public_export", True) is not False
    grades = {str(source.get("reliability_grade", "")) for source in (source_rows or [])}
    if not public_export:
        return "internal_only"
    if privacy and privacy != "clear":
        return "needs_privacy_review"
    if status in {"excluded_from_public_script", "false_or_retracted"}:
        return "excluded_or_retracted"
    if status in {"disputed", "unverified"}:
        return "lead_or_disputed"
    if status == "single_source":
        return "source_note_required"
    if status in {"verified", "corroborated"} and grades and grades <= {"A", "B"}:
        return "public_ready"
    if status in {"verified", "corroborated"}:
        return "usable_with_context"
    return "review_needed"


def record_id_for(row: dict[str, Any]) -> str:
    for key in ["claim_id", "event_id", "event_link_id", "rel_id", "entity_id", "source_id"]:
        if row.get(key):
            return str(row[key])
    return ""


def public_ready_record(row: dict[str, Any]) -> bool:
    privacy = str(row.get("privacy_review", "clear") or "clear")
    return row.get("public_export", True) is not False and privacy == "clear"


def best_grade(source_rows: list[dict[str, Any]], packs: VocabPacks | None = None) -> str:
    scores = (packs or load_default_packs()).grade_scores
    return max((str(source.get("reliability_grade", "")) for source in source_rows), key=lambda grade: scores.get(grade, 0.0), default="")


def source_grade_counts(source_rows: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for source in source_rows:
        grade = str(source.get("reliability_grade", "") or "unknown")
        counts[grade] = counts.get(grade, 0) + 1
    return ";".join(f"{grade}:{counts[grade]}" for grade in sorted(counts))


def weakest_status(statuses: list[str], packs: VocabPacks | None = None) -> str:
    scores = (packs or load_default_packs()).status_scores
    return min(statuses, key=lambda status: scores.get(status, 0.0), default="")


def boundary_signal(row: dict[str, Any]) -> bool:
    text = " ".join(str(row.get(key, "")) for key in ["claim", "claim_type", "relation_type", "event_type", "title", "notes", "status"]).lower()
    return bool(parse_cell_list(row.get("contradicts"))) or any(
        term in text
        for term in [
            "boundary",
            "contradict",
            "disputed",
            "unverified",
            "lead-only",
            "lead only",
            "not verified",
            "not proof",
            "unclear",
            "category bridge",
            "context only",
        ]
    )
