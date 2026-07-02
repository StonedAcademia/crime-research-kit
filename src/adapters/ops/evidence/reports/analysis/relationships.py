"""Relationship-family and class classifiers, driven by vocabulary packs."""

from __future__ import annotations

from typing import Any

from adapters.ops.evidence.reports.analysis.vocabulary import VocabPacks, load_default_packs, match_pack
from adapters.ops.evidence.reports.common import RELATIONSHIP_CLASS_TITLES


def relation_family(relation_type: str, record_kind: str = "relationship", packs: VocabPacks | None = None) -> str:
    rel = relation_type.lower()
    if "co_mentioned" in rel:
        return "lead_only_co_mentions"
    if record_kind == "event_link":
        return "event_context"
    active = packs or load_default_packs()
    return match_pack(rel, active.relation_families) or "unclassified"


def relationship_class(record: dict[str, Any], record_kind: str = "relationship", packs: VocabPacks | None = None) -> str:
    explicit = str(record.get("relationship_class") or "").strip()
    if explicit in RELATIONSHIP_CLASS_TITLES:
        return explicit
    relation_type = str(record.get("relation_type", "")).lower()
    status = str(record.get("status", "")).lower()
    text = " ".join(
        str(record.get(field) or "").lower()
        for field in ("rel_id", "event_link_id", "claim_id", "relation_type", "status", "notes", "basis", "summary")
    )
    if "co_mentioned" in relation_type:
        return "hypothesis_requires_more_sources"
    active = packs or load_default_packs()
    matched = match_pack(text, active.relationship_classes)
    if matched in {"documented_successor", "method_diffusion", "narrative_inheritance"}:
        return matched
    if status == "disputed" or matched == "contested_overlap":
        return "contested_overlap"
    if status == "unverified" or "lead" in text:
        return "hypothesis_requires_more_sources"
    if record_kind == "event_link" or matched == "personnel_bridge":
        return "personnel_bridge"
    return matched or "unclassified"
