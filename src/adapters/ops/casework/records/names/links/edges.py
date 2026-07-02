"""Private co-mention event links and relationships."""

from __future__ import annotations

from itertools import combinations
from typing import Any

from core.casefile import stable_id

from ..matching import append_if_new, clean_id_list, co_mention_note, contains_name, pair_ids


def link_events(case_dir: str, resolved: list[dict[str, Any]], events: list[dict[str, Any]], context: dict[str, Any], counts: dict[str, int]) -> dict[str, set[str]]:
    event_to_entities: dict[str, set[str]] = {}
    for event in events:
        event_id = str(event.get("event_id", ""))
        event_sources = clean_id_list(event.get("source_ids"))
        if not event_id or not event_sources:
            continue
        matched = _matched_for_event(resolved, event, event_sources)
        if not matched:
            continue
        event_to_entities[event_id] = set(matched)
        _write_event_links(case_dir, event, matched, context, counts)
        _write_event_relationships(case_dir, event, matched, context, counts)
    return event_to_entities


def link_sources(case_dir: str, resolved: list[dict[str, Any]], context: dict[str, Any], counts: dict[str, int]) -> None:
    source_to_entities: dict[str, set[str]] = {}
    for item in resolved:
        entity_id = str(item["entity"].get("entity_id", ""))
        for source_id in item.get("source_ids", set()):
            if entity_id:
                source_to_entities.setdefault(source_id, set()).add(entity_id)
    for source_id, entity_set in sorted(source_to_entities.items()):
        for left, right in combinations(sorted(entity_set), 2):
            src_entity_id, dst_entity_id = pair_ids(left, right)
            rel = _relationship(src_entity_id, dst_entity_id, "source", source_id, [source_id], [], None, None, 0.25)
            _append_relationship(case_dir, rel, context, counts)


def _matched_for_event(resolved: list[dict[str, Any]], event: dict[str, Any], event_sources: list[str]) -> dict[str, set[str]]:
    matched: dict[str, set[str]] = {}
    event_entities = set(clean_id_list(event.get("entity_ids")))
    event_text = " ".join(str(event.get(field, "")) for field in ("title", "notes"))
    for item in resolved:
        entity_id = str(item["entity"].get("entity_id", ""))
        if not entity_id:
            continue
        basis = set()
        if entity_id in event_entities:
            basis.add("existing_event_entity_id")
        if set(event_sources) & set(item.get("source_ids", set())):
            basis.add("source_text_cooccurrence")
        if event_text and any(contains_name(event_text, alias) for alias in item["entry"]["aliases"]):
            basis.add("event_text_name_match")
        if basis:
            matched[entity_id] = basis
    return matched


def _write_event_links(case_dir: str, event: dict[str, Any], matched: dict[str, set[str]], context: dict[str, Any], counts: dict[str, int]) -> None:
    event_id = str(event.get("event_id"))
    for entity_id, basis in matched.items():
        link = {
            "event_link_id": stable_id("EL", entity_id, event_id, "co_mentioned_in_event"),
            "entity_id": entity_id,
            "event_id": event_id,
            "relation_type": "co_mentioned_in_event",
            "basis": ";".join(sorted(basis)),
            "claim_ids": clean_id_list(event.get("claim_ids")),
            "source_ids": clean_id_list(event.get("source_ids")),
            "confidence": 0.45 if "existing_event_entity_id" in basis else 0.3,
            "status": "unverified",
            "public_export": False,
            "notes": co_mention_note(f"event {event_id}"),
        }
        if append_if_new(case_dir, "event_links", link, "event_link_id", context["event_link_ids"]):
            counts["event_links_created"] += 1
        else:
            counts["duplicate_records_skipped"] += 1


def _write_event_relationships(case_dir: str, event: dict[str, Any], matched: dict[str, set[str]], context: dict[str, Any], counts: dict[str, int]) -> None:
    event_id = str(event.get("event_id"))
    for left, right in combinations(sorted(matched), 2):
        src_entity_id, dst_entity_id = pair_ids(left, right)
        rel = _relationship(
            src_entity_id,
            dst_entity_id,
            "event",
            event_id,
            clean_id_list(event.get("source_ids")),
            clean_id_list(event.get("claim_ids")),
            event.get("start_date"),
            event.get("end_date"),
            0.3,
        )
        _append_relationship(case_dir, rel, context, counts)


def _relationship(src_entity_id: str, dst_entity_id: str, scope: str, anchor: str, source_ids: list[str], claim_ids: list[str], start_date: Any, end_date: Any, confidence: float) -> dict[str, Any]:
    return {
        "rel_id": stable_id("R", src_entity_id, dst_entity_id, "co_mentioned_with", anchor),
        "src_entity_id": src_entity_id,
        "dst_entity_id": dst_entity_id,
        "relation_type": "co_mentioned_with",
        "start_date": start_date,
        "end_date": end_date,
        "claim_ids": claim_ids,
        "source_ids": source_ids,
        "confidence": confidence,
        "status": "unverified",
        "public_export": False,
        "notes": co_mention_note(f"{scope} {anchor}"),
    }


def _append_relationship(case_dir: str, rel: dict[str, Any], context: dict[str, Any], counts: dict[str, int]) -> None:
    if append_if_new(case_dir, "relationships", rel, "rel_id", context["rel_ids"]):
        counts["relationships_created"] += 1
    else:
        counts["duplicate_records_skipped"] += 1
