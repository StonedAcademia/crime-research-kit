"""`link-names` command implementation."""

from __future__ import annotations

import argparse
import json
from typing import Any

from crime_research_kit._runtime.core.casefile import case_path, ensure_case, log_action, read_jsonl, record_path, write_jsonl

from ..workspace import load_sources
from .links.edges import link_events, link_sources
from .matching import (
    append_if_new,
    build_entity_index,
    entity_lookup_keys,
    find_entity_for_entry,
    make_candidate_entity,
    read_source_texts,
    refresh_entity_from_name_entry,
    source_matches_for_entry,
)
from .parsing import parse_name_entries
from .reports.brief import write_name_link_research_brief


def link_names(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    entries = parse_name_entries(args.name, args.names_file)
    if not entries:
        raise SystemExit("Provide at least one --name or --names-file entry")
    sources, entities, events, relationships, event_links = _load_records(args.case_dir)
    context = _context(entities, relationships, event_links)
    counts = _counts(len(entries))
    resolved, changed = _resolve_entries(
        args.case_dir,
        entries,
        read_source_texts(args.case_dir, sources),
        entities,
        context,
        counts,
    )
    if changed:
        write_jsonl(record_path(args.case_dir, "entities"), entities)
    event_to_entities = link_events(args.case_dir, resolved, events, context, counts)
    link_sources(args.case_dir, resolved, context, counts)
    brief_path = write_name_link_research_brief(
        args.case_dir,
        entries=entries,
        resolved=resolved,
        events=events,
        sources=sources,
        source_texts=read_source_texts(args.case_dir, sources),
        counts=counts,
    )
    log_action(
        args.case_dir,
        "link_names",
        {
            "names": [entry["primary"] for entry in entries],
            "counts": counts,
            "research_brief": str(brief_path.relative_to(case_path(args.case_dir))),
            "event_to_entities": {key: sorted(value) for key, value in event_to_entities.items()},
            "resolved_entity_ids": sorted(_resolved_by_entity_id(resolved)),
        },
    )
    print(json.dumps({"counts": counts, "research_brief": str(brief_path)}, indent=2, ensure_ascii=False))


def _load_records(case_dir: str) -> tuple[list[dict[str, Any]], ...]:
    return (
        load_sources(case_dir),
        read_jsonl(record_path(case_dir, "entities")),
        read_jsonl(record_path(case_dir, "events")),
        read_jsonl(record_path(case_dir, "relationships")),
        read_jsonl(record_path(case_dir, "event_links")),
    )


def _counts(input_names: int) -> dict[str, int]:
    return {
        "input_names": input_names,
        "matched_existing_entities": 0,
        "candidate_entities_created": 0,
        "entities_refreshed": 0,
        "event_links_created": 0,
        "relationships_created": 0,
        "duplicate_records_skipped": 0,
    }


def _context(entities: list[dict[str, Any]], relationships: list[dict[str, Any]], event_links: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "entity_index": build_entity_index(entities),
        "entity_ids": {str(entity.get("entity_id")) for entity in entities if entity.get("entity_id")},
        "rel_ids": {str(rel.get("rel_id")) for rel in relationships if rel.get("rel_id")},
        "event_link_ids": {str(link.get("event_link_id")) for link in event_links if link.get("event_link_id")},
    }


def _resolve_entries(
    case_dir: str,
    entries: list[dict[str, Any]],
    source_texts: dict[str, str],
    entities: list[dict[str, Any]],
    context: dict[str, Any],
    counts: dict[str, int],
) -> tuple[list[dict[str, Any]], bool]:
    changed = False
    resolved = []
    for entry in entries:
        matched_sources = source_matches_for_entry(entry, source_texts)
        entity = find_entity_for_entry(entry, context["entity_index"])
        if entity:
            counts["matched_existing_entities"] += 1
            changed = _refresh_entity(entity, entry, matched_sources, entities, context, counts) or changed
        else:
            entity, created, refreshed = _candidate_or_existing(case_dir, entry, matched_sources, entities, context)
            counts["candidate_entities_created"] += int(created)
            counts["entities_refreshed"] += int(refreshed)
            counts["duplicate_records_skipped"] += int(not created and not refreshed)
            changed = changed or refreshed
        resolved.append({"entry": entry, "entity": entity, "source_ids": matched_sources})
    return resolved, changed


def _refresh_entity(entity: dict[str, Any], entry: dict[str, Any], matched_sources: set[str], entities: list[dict[str, Any]], context: dict[str, Any], counts: dict[str, int]) -> bool:
    if not refresh_entity_from_name_entry(entity, entry, matched_sources):
        return False
    counts["entities_refreshed"] += 1
    context["entity_index"] = build_entity_index(entities)
    return True


def _candidate_or_existing(case_dir: str, entry: dict[str, Any], matched_sources: set[str], entities: list[dict[str, Any]], context: dict[str, Any]) -> tuple[dict[str, Any], bool, bool]:
    entity = make_candidate_entity(entry, matched_sources)
    if append_if_new(case_dir, "entities", entity, "entity_id", context["entity_ids"]):
        entities.append(entity)
        for key in entity_lookup_keys(entity):
            context["entity_index"].setdefault(key, entity)
        return entity, True, False
    existing = next((row for row in entities if row.get("entity_id") == entity.get("entity_id")), None)
    if existing and refresh_entity_from_name_entry(existing, entry, matched_sources):
        context["entity_index"] = build_entity_index(entities)
        return existing, False, True
    return existing or entity, False, False


def _resolved_by_entity_id(resolved: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["entity"].get("entity_id")): item for item in resolved if item["entity"].get("entity_id")}
