"""Boundary and readiness data products for analysis exports."""

from __future__ import annotations

from typing import Any

from adapters.ops.evidence.reports.analysis.classifiers import (
    best_grade,
    boundary_signal,
    readiness_label,
    source_grade_counts,
)
from adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from adapters.ops.evidence.reports.analysis.relationships import relationship_class
from adapters.ops.evidence.reports.common import parse_cell_list


def build_boundary_rows(ctx: AnalysisContext) -> list[dict[str, Any]]:
    boundary_rows: list[dict[str, Any]] = []
    for claim in ctx.claims:
        claim_type = str(claim.get("claim_type", ""))
        status = str(claim.get("status", ""))
        contradicts = parse_cell_list(claim.get("contradicts"))
        if claim_type == "contradiction_or_boundary" or contradicts or status in {"disputed", "unverified", "excluded_from_public_script"}:
            boundary_rows.append({
                "record_id": claim.get("claim_id", ""),
                "record_type": "claim",
                "status": status,
                "claim_type": claim_type,
                "boundary_kind": "contradicts" if contradicts else claim_type or status,
                "summary": claim.get("claim", ""),
                "source_ids": claim.get("source_ids", []),
                "contradicts": contradicts,
            })
    for rel in ctx.relationships:
        notes = str(rel.get("notes", "")).lower()
        if boundary_signal(rel) or any(term in notes for term in ["boundary", "lead", "alleged", "not verified", "do not treat"]):
            boundary_rows.append({
                "record_id": rel.get("rel_id", ""),
                "record_type": "relationship",
                "status": rel.get("status", ""),
                "claim_type": "",
                "boundary_kind": "relationship_note",
                "relationship_class": relationship_class(rel),
                "summary": rel.get("notes", ""),
                "source_ids": rel.get("source_ids", []),
                "contradicts": "",
            })
    for link in ctx.event_links:
        if boundary_signal(link):
            boundary_rows.append({
                "record_id": link.get("event_link_id", ""),
                "record_type": "event_link",
                "status": link.get("status", ""),
                "claim_type": "",
                "boundary_kind": "event_link_context",
                "relationship_class": relationship_class(link, "event_link"),
                "summary": link.get("notes", "") or link.get("basis", ""),
                "source_ids": link.get("source_ids", []),
                "contradicts": "",
            })
    return boundary_rows


def build_readiness_products(ctx: AnalysisContext) -> dict[str, list[dict[str, Any]]]:
    readiness_rows: list[dict[str, Any]] = []
    for record_type, rows, id_key in [
        ("claim", ctx.claims, "claim_id"),
        ("event", ctx.events, "event_id"),
        ("event_link", ctx.event_links, "event_link_id"),
        ("relationship", ctx.relationships, "rel_id"),
    ]:
        for row in rows:
            source_rows = ctx.source_rows_for_ids(parse_cell_list(row.get("source_ids")))
            boundary = boundary_signal(row)
            readiness_rows.append({
                "record_type": record_type,
                "record_id": row.get(id_key, ""),
                "status": row.get("status", ""),
                "confidence": row.get("confidence", ""),
                "source_count": len(source_rows),
                "best_source_grade": best_grade(source_rows),
                "source_grade_counts": source_grade_counts(source_rows),
                "public_export": row.get("public_export", True),
                "privacy_review": row.get("privacy_review", "clear"),
                "readiness": readiness_label(row, source_rows),
                "boundary_flag": boundary,
                "required_caveat": "Boundary/lead/context wording required." if boundary else "",
                "relationship_class": relationship_class(row, record_type) if record_type in {"event_link", "relationship"} else "",
                "summary": row.get("claim") or row.get("title") or row.get("notes", ""),
            })
    readiness_count_map: dict[str, int] = {}
    for row in readiness_rows:
        readiness = str(row.get("readiness", ""))
        readiness_count_map[readiness] = readiness_count_map.get(readiness, 0) + 1
    readiness_counts = [{"readiness": key, "count": value} for key, value in sorted(readiness_count_map.items())]
    return {"readiness_rows": readiness_rows, "readiness_counts": readiness_counts}
