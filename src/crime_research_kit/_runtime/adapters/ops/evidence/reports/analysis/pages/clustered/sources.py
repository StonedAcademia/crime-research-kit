"""Subproject source and timeline products for clustered visuals."""

from __future__ import annotations

from collections import Counter
from typing import Any

from crime_research_kit._runtime.adapters.ops.evidence.ledger.scoring import date_sort_key
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.clustered.rules import (
    cluster_for,
    semantic_facets,
    subproject_number,
    subproject_numbers,
)
from crime_research_kit._runtime.adapters.ops.evidence.reports.common import parse_cell_list


def subproject_index(ctx: AnalysisContext, node_by_id: dict[str, dict[str, Any]]) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}

    def ensure(num: int, label: str = "", node: dict[str, Any] | None = None) -> dict[str, Any]:
        cid, cluster_label = cluster_for("event_series", f"Subproject {num}", label)
        item = rows.setdefault(num, {
            "subproject_number": num,
            "subproject_id": f"E_SUBPROJ_{num}",
            "label": label or f"MKULTRA Subproject {num}",
            "source_ids": set(),
            "claim_ids": set(),
            "event_ids": set(),
            "relationship_ids": set(),
            "source_counts": Counter(),
            "facets": set(),
            "statuses": set(),
            "cluster_id": cid,
            "cluster_label": cluster_label,
            "readiness": "",
        })
        if node:
            item["subproject_id"] = node.get("node_id") or item["subproject_id"]
            item["label"] = node.get("label") or item["label"]
            item["cluster_id"] = node.get("cluster_id") or item["cluster_id"]
            item["cluster_label"] = node.get("cluster_label") or item["cluster_label"]
            item["readiness"] = node.get("readiness", "")
        return item

    for node in node_by_id.values():
        num = subproject_number(node.get("node_id"), node.get("label"))
        if num is not None:
            ensure(num, str(node.get("label", "")), node)
    for kind, records in [("claim", ctx.claims), ("event", ctx.events), ("relationship", ctx.relationships), ("event_link", ctx.event_links), ("entity", ctx.entities)]:
        for record in records:
            text = _record_text(record)
            nums = subproject_numbers(text)
            if not nums:
                continue
            for num in nums:
                item = ensure(num)
                item["facets"].update(semantic_facets(text))
                source_ids = parse_cell_list(record.get("source_ids"))
                claim_ids = parse_cell_list(record.get("claim_ids"))
                if kind == "claim":
                    claim_ids.append(str(record.get("claim_id", "")))
                for source_id in source_ids:
                    item["source_ids"].add(source_id)
                    item["source_counts"][source_id] += 1
                item["claim_ids"].update(claim_id for claim_id in claim_ids if claim_id)
                if kind == "event":
                    item["event_ids"].add(str(record.get("event_id", "")))
                if kind == "relationship":
                    item["relationship_ids"].add(str(record.get("rel_id", "")))
                if record.get("status"):
                    item["statuses"].add(str(record.get("status")))
    return rows


def subproject_matrix(subprojects: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for num, item in sorted(subprojects.items()):
        rows.append({
            "subproject_number": num,
            "subproject_id": item["subproject_id"],
            "label": item["label"],
            "cluster_id": item["cluster_id"],
            "cluster_label": item["cluster_label"],
            "source_count": len(item["source_ids"]),
            "claim_count": len(item["claim_ids"]),
            "event_count": len(item["event_ids"]),
            "relationship_count": len(item["relationship_ids"]),
            "status": ";".join(sorted(item["statuses"])),
            "readiness": item["readiness"] or "review_needed",
            "facet_types": ";".join(sorted(item["facets"])),
            "source_ids": sorted(item["source_ids"]),
            "claim_ids": sorted(item["claim_ids"]),
        })
    return rows


def source_subproject_edges(ctx: AnalysisContext, subprojects: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for num, item in sorted(subprojects.items()):
        for source_id, count in sorted(item["source_counts"].items()):
            source = ctx.source_by_id.get(source_id, {})
            rows.append({
                "source_id": source_id,
                "source_title": source.get("title", source_id),
                "source_grade": source.get("reliability_grade", ""),
                "subproject_number": num,
                "subproject_id": item["subproject_id"],
                "subproject_label": item["label"],
                "cluster_id": item["cluster_id"],
                "cluster_label": item["cluster_label"],
                "record_count": count,
                "edge_weight": round(min(2.0, 0.35 + count * 0.12), 3),
                "status": ";".join(sorted(item["statuses"])),
                "readiness": item["readiness"] or "review_needed",
                "facet_types": ";".join(sorted(item["facets"])),
            })
    return rows


def cluster_timeline(ctx: AnalysisContext) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in ctx.events:
        text = _record_text(event)
        nums = set(subproject_numbers(text))
        clusters = [cluster_for("event", text)] if not nums else [cluster_for("event_series", f"Subproject {num}", text) for num in sorted(nums)]
        for cid, label in dict(clusters).items():
            rows.append({
                "cluster_id": cid,
                "cluster_label": label,
                "event_id": event.get("event_id", ""),
                "event_title": event.get("title", ""),
                "start_date": event.get("start_date", ""),
                "end_date": event.get("end_date", ""),
                "date_precision": event.get("date_precision", ""),
                "event_type": event.get("event_type", ""),
                "subproject_numbers": ";".join(str(num) for num in sorted(nums)),
                "status": event.get("status", ""),
                "confidence": event.get("confidence", ""),
                "source_count": len(parse_cell_list(event.get("source_ids"))),
                "source_ids": event.get("source_ids", []),
                "claim_ids": event.get("claim_ids", []),
            })
    return sorted(rows, key=lambda row: (str(row["cluster_id"]), date_sort_key(row.get("start_date")), str(row["event_id"])))


def _record_text(record: dict[str, Any]) -> str:
    return " ".join(str(value) for value in record.values())
