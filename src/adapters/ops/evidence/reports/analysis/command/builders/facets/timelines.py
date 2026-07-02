"""Temporal swimlane data products for analysis exports."""

from __future__ import annotations

from typing import Any

from adapters.ops.evidence.reports.analysis.classifiers import public_ready_record
from adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from adapters.ops.evidence.reports.analysis.relationships import relationship_class
from adapters.ops.evidence.reports.common import entity_display, parse_cell_list
from adapters.ops.evidence.shared.scoring import date_sort_key


def build_swimlanes(ctx: AnalysisContext) -> list[dict[str, Any]]:
    swimlanes: list[dict[str, Any]] = []
    event_by_id = {str(event.get("event_id")): event for event in ctx.events}
    seen_swimlane_keys: set[tuple[str, str, str]] = set()
    for link in ctx.event_links:
        event_id = str(link.get("event_id", ""))
        event = event_by_id.get(event_id, {})
        entity_id = str(link.get("entity_id", ""))
        cluster_id = ctx.cluster_by_person.get(entity_id, "unclustered")
        key = (cluster_id, event_id, str(link.get("event_link_id", "")))
        seen_swimlane_keys.add(key)
        swimlanes.append({
            "cluster_id": cluster_id,
            "cluster_label": ctx.cluster_labels.get(cluster_id, cluster_id),
            "entity_id": entity_id,
            "name": entity_display(ctx.entity_by_id.get(entity_id)),
            "start_date": event.get("start_date", ""),
            "end_date": event.get("end_date", ""),
            "date_precision": event.get("date_precision", ""),
            "event_id": event_id,
            "event_title": event.get("title", ""),
            "event_type": event.get("event_type", ""),
            "status": event.get("status", ""),
            "confidence": event.get("confidence", ""),
            "event_link_id": link.get("event_link_id", ""),
            "relation_type": link.get("relation_type", ""),
            "relationship_class": relationship_class(link, "event_link"),
            "event_link_status": link.get("status", ""),
            "event_link_confidence": link.get("confidence", ""),
            "source_count": len(set(parse_cell_list(event.get("source_ids"))) | set(parse_cell_list(link.get("source_ids")))),
            "claim_ids": sorted(set(parse_cell_list(event.get("claim_ids"))) | set(parse_cell_list(link.get("claim_ids")))),
            "source_ids": sorted(set(parse_cell_list(event.get("source_ids"))) | set(parse_cell_list(link.get("source_ids")))),
            "is_public_safe": public_ready_record(event) and public_ready_record(link),
            "caveat": "co-mention/context link" if "co_mentioned" in str(link.get("relation_type", "")) else "",
        })
    for event in ctx.events:
        _append_event_swimlanes(ctx, event, seen_swimlane_keys, swimlanes)
    swimlanes.sort(key=lambda row: (str(row["cluster_id"]), date_sort_key(row.get("start_date")), str(row["event_id"])))
    return swimlanes


def _append_event_swimlanes(
    ctx: AnalysisContext,
    event: dict[str, Any],
    seen_swimlane_keys: set[tuple[str, str, str]],
    swimlanes: list[dict[str, Any]],
) -> None:
    event_id = str(event.get("event_id", ""))
    for entity_id in parse_cell_list(event.get("entity_ids")) or [""]:
        cluster_id = ctx.cluster_by_person.get(entity_id, "unclustered")
        key = (cluster_id, event_id, "")
        if key in seen_swimlane_keys:
            continue
        swimlanes.append({
            "cluster_id": cluster_id,
            "cluster_label": ctx.cluster_labels.get(cluster_id, cluster_id),
            "entity_id": entity_id,
            "name": entity_display(ctx.entity_by_id.get(entity_id)),
            "start_date": event.get("start_date", ""),
            "end_date": event.get("end_date", ""),
            "date_precision": event.get("date_precision", ""),
            "event_id": event_id,
            "event_title": event.get("title", ""),
            "event_type": event.get("event_type", ""),
            "status": event.get("status", ""),
            "confidence": event.get("confidence", ""),
            "event_link_id": "",
            "relation_type": "event_entity",
            "relationship_class": "personnel_bridge",
            "event_link_status": "",
            "event_link_confidence": "",
            "source_count": len(parse_cell_list(event.get("source_ids"))),
            "claim_ids": event.get("claim_ids", []),
            "source_ids": event.get("source_ids", []),
            "is_public_safe": public_ready_record(event),
            "caveat": "",
        })
