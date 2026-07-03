"""Evidence quality data products for analysis chart exports."""

from __future__ import annotations

from typing import Any

from adapters.ops.evidence.reports.analysis.classifiers import (
    best_grade,
    boundary_signal,
    public_ready_record,
    readiness_label,
    source_grade_counts,
    source_grade_score,
    status_score,
)
from adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from adapters.ops.evidence.reports.analysis.command.builders.sources import build_source_dashboard
from adapters.ops.evidence.reports.common import parse_cell_list
from adapters.ops.evidence.reports.weights import parse_float


def build_evidence_products(ctx: AnalysisContext) -> dict[str, list[dict[str, Any]]]:
    claim_heatmap, claim_matrix, claim_edge_rows = _claim_products(ctx)
    heatmap_aggregate = _heatmap_aggregate(claim_heatmap)
    source_dashboard, source_grade_count_rows = build_source_dashboard(ctx)
    return {
        "claim_heatmap": claim_heatmap,
        "claim_matrix": claim_matrix,
        "claim_edge_rows": claim_edge_rows,
        "heatmap_aggregate": heatmap_aggregate,
        "source_dashboard": source_dashboard,
        "source_grade_count_rows": source_grade_count_rows,
    }


def _claim_products(
    ctx: AnalysisContext,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    claim_heatmap: list[dict[str, Any]] = []
    claim_matrix: list[dict[str, Any]] = []
    claim_edge_rows: list[dict[str, Any]] = []
    for claim in sorted(ctx.claims, key=lambda row: str(row.get("claim_id", ""))):
        source_ids = [sid for sid in parse_cell_list(claim.get("source_ids")) if sid in ctx.source_by_id]
        source_rows = [ctx.source_by_id[sid] for sid in source_ids]
        independent_count = ctx.independent_source_count(source_rows)
        claim_heatmap.append({
            "claim_id": claim.get("claim_id", ""),
            "claim": claim.get("claim", ""),
            "claim_type": claim.get("claim_type", ""),
            "status": claim.get("status", ""),
            "confidence": claim.get("confidence", ""),
            "status_score": status_score(str(claim.get("status", "")), packs=ctx.packs),
            "source_count": len(source_rows),
            "independent_source_count": independent_count,
            "best_source_grade": best_grade(source_rows, packs=ctx.packs),
            "source_grade_counts": source_grade_counts(source_rows),
            "source_grade_score": source_grade_score(source_rows, packs=ctx.packs),
            "privacy_review": claim.get("privacy_review", ""),
            "public_export": claim.get("public_export", True),
            "boundary_flag": boundary_signal(claim),
            "readiness": readiness_label(claim, source_rows),
        })
        _append_claim_matrix_rows(claim_matrix, claim, source_rows)
        _append_claim_edge_rows(claim_edge_rows, ctx, claim, source_ids)
    return claim_heatmap, claim_matrix, claim_edge_rows


def _append_claim_matrix_rows(
    claim_matrix: list[dict[str, Any]],
    claim: dict[str, Any],
    source_rows: list[dict[str, Any]],
) -> None:
    for source in source_rows:
        claim_matrix.append({
            "claim_id": claim.get("claim_id", ""),
            "claim_label": str(claim.get("claim", ""))[:160],
            "source_id": source.get("source_id", ""),
            "source_title": source.get("title", ""),
            "source_grade": source.get("reliability_grade", ""),
            "source_type": source.get("source_type", ""),
            "source_publisher": source.get("publisher", ""),
            "claim_status": claim.get("status", ""),
            "claim_confidence": claim.get("confidence", ""),
            "claim_type": claim.get("claim_type", ""),
            "source_role": "boundary_source" if boundary_signal(claim) else "direct_support",
            "safe_public_cell": public_ready_record(claim) and source.get("public_export", True) is not False,
            "boundary_flag": boundary_signal(claim),
            "contradiction_flag": bool(parse_cell_list(claim.get("contradicts"))),
            "contradicts": claim.get("contradicts", []),
            "supports": claim.get("supports", []),
        })


def _append_claim_edge_rows(
    claim_edge_rows: list[dict[str, Any]],
    ctx: AnalysisContext,
    claim: dict[str, Any],
    source_ids: list[str],
) -> None:
    for edge_type, linked_ids in [("supports", parse_cell_list(claim.get("supports"))), ("contradicts", parse_cell_list(claim.get("contradicts")))]:
        for linked_id in linked_ids:
            linked = ctx.claim_by_id.get(linked_id, {})
            claim_edge_rows.append({
                "from_claim_id": claim.get("claim_id", ""),
                "to_claim_id": linked_id,
                "edge_type": edge_type,
                "from_claim_status": claim.get("status", ""),
                "to_claim_status": linked.get("status", ""),
                "from_confidence": claim.get("confidence", ""),
                "to_confidence": linked.get("confidence", ""),
                "shared_source_count": len(set(source_ids) & set(parse_cell_list(linked.get("source_ids")))),
                "from_source_ids": source_ids,
                "to_source_ids": parse_cell_list(linked.get("source_ids")),
                "boundary_flag": edge_type == "contradicts" or boundary_signal(claim) or boundary_signal(linked),
                "safe_public_pair": public_ready_record(claim) and (not linked or public_ready_record(linked)),
            })


def _heatmap_aggregate(claim_heatmap: list[dict[str, Any]]) -> list[dict[str, Any]]:
    heatmap_groups: dict[tuple[str, str], dict[str, Any]] = {}
    for row in claim_heatmap:
        key = (str(row.get("claim_type") or "unknown"), str(row.get("status") or "unknown"))
        group = heatmap_groups.setdefault(key, _heatmap_bucket(key))
        group["claim_count"] += 1
        group["public_claim_count"] += 1 if row.get("public_export") is not False else 0
        group["internal_only_count"] += 1 if row.get("public_export") is False else 0
        group["needs_review_count"] += 1 if row.get("privacy_review") and row.get("privacy_review") != "clear" else 0
        group["confidence_total"] += parse_float(row.get("confidence"), 0.0)
        group["source_count_total"] += int(row.get("source_count") or 0)
        group["boundary_claim_count"] += 1 if row.get("boundary_flag") else 0
        group["claim_ids"].append(row.get("claim_id", ""))
        grade_map = dict(part.split(":", 1) for part in str(row.get("source_grade_counts", "")).split(";") if ":" in part)
        group["a_sources"] += int(grade_map.get("A", "0"))
        group["b_sources"] += int(grade_map.get("B", "0"))
        group["c_sources"] += int(grade_map.get("C", "0"))
        group["d_sources"] += int(grade_map.get("D", "0"))
    heatmap_aggregate = []
    for group in heatmap_groups.values():
        count = max(1, int(group["claim_count"]))
        group["avg_confidence"] = round(float(group.pop("confidence_total")) / count, 3)
        group["avg_source_count"] = round(float(group["source_count_total"]) / count, 3)
        heatmap_aggregate.append(group)
    heatmap_aggregate.sort(key=lambda row: (str(row["claim_type"]), str(row["status"])))
    return heatmap_aggregate


def _heatmap_bucket(key: tuple[str, str]) -> dict[str, Any]:
    return {
        "claim_type": key[0],
        "status": key[1],
        "claim_count": 0,
        "public_claim_count": 0,
        "internal_only_count": 0,
        "needs_review_count": 0,
        "confidence_total": 0.0,
        "source_count_total": 0,
        "a_sources": 0,
        "b_sources": 0,
        "c_sources": 0,
        "d_sources": 0,
        "boundary_claim_count": 0,
        "claim_ids": [],
    }
