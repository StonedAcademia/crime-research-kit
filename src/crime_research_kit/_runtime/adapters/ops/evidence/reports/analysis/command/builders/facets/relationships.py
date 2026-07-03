"""Relationship class aggregation for analysis exports."""

from __future__ import annotations

from typing import Any

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.classifiers import boundary_signal, status_score
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.relationships import relation_family, relationship_class
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.vocabulary import VocabPacks
from crime_research_kit._runtime.adapters.ops.evidence.reports.common import RELATIONSHIP_CLASS_TITLES, parse_cell_list


def build_relation_type_counts(ctx: AnalysisContext) -> list[dict[str, Any]]:
    relation_counts: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for rel in ctx.relationships:
        _add_relation_count(relation_counts, rel, "relationship", ctx.packs)
    for link in ctx.event_links:
        _add_relation_count(relation_counts, link, "event_link", ctx.packs)
    return [
        row
        for row in sorted(relation_counts.values(), key=lambda item: (-float(item["weighted_count"]), str(item["relation_type"])))
    ]


def _add_relation_count(
    relation_counts: dict[tuple[str, str, str, str], dict[str, Any]],
    row: dict[str, Any],
    record_kind: str,
    packs: VocabPacks,
) -> None:
    relation_type = str(row.get("relation_type", ""))
    rel_class = relationship_class(row, record_kind if record_kind == "event_link" else "relationship", packs=packs)
    status = str(row.get("status", ""))
    family = relation_family(relation_type, record_kind, packs=packs)
    public_scope = "public" if row.get("public_export", True) is not False else "internal"
    key = (record_kind, rel_class, family, relation_type, status + "/" + public_scope)
    bucket = relation_counts.setdefault(key, {
        "record_kind": record_kind,
        "relationship_class": rel_class,
        "relationship_class_label": RELATIONSHIP_CLASS_TITLES.get(rel_class, rel_class),
        "relation_family": family,
        "relation_type": relation_type,
        "status": status,
        "public_scope": public_scope,
        "row_count": 0,
        "weighted_count": 0.0,
        "source_count": 0,
        "claim_count": 0,
        "boundary_count": 0,
        "lead_only_count": 0,
        "sample_record_ids": [],
    })
    bucket["row_count"] += 1
    weight = status_score(status, packs=packs) or 0.3
    if "co_mentioned" in relation_type:
        weight *= 0.1
        bucket["lead_only_count"] += 1
    bucket["weighted_count"] = round(float(bucket["weighted_count"]) + weight, 3)
    bucket["source_count"] += len(parse_cell_list(row.get("source_ids")))
    bucket["claim_count"] += len(parse_cell_list(row.get("claim_ids")))
    bucket["boundary_count"] += 1 if boundary_signal(row) else 0
    id_key = "event_link_id" if record_kind == "event_link" else "rel_id"
    if len(bucket["sample_record_ids"]) < 8:
        bucket["sample_record_ids"].append(row.get(id_key, ""))
