"""Identity-resolution candidate reporting."""

from __future__ import annotations

import argparse
import json
from typing import Any

from core.casefile import case_path, ensure_case, log_action, now_utc, read_jsonl, record_path, stable_id, today, write_json

from ...casework.records.names.matching import clean_id_list
from ..shared.records import compact_record, normalize_match_text, report_out_path


def entity_resolution_context(
    entity: dict[str, Any],
    *,
    claims: list[dict[str, Any]],
    events: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    event_links: list[dict[str, Any]],
) -> dict[str, Any]:
    entity_id = str(entity.get("entity_id", ""))
    claim_ids = set(clean_id_list(entity.get("claim_ids")))
    claim_ids.update(
        str(claim.get("claim_id"))
        for claim in claims
        if entity_id and entity_id in " ".join(str(claim.get(field, "")) for field in ("claim", "notes"))
    )
    event_ids = {str(event.get("event_id")) for event in events if entity_id in clean_id_list(event.get("entity_ids"))}
    event_ids.update(str(link.get("event_id")) for link in event_links if str(link.get("entity_id")) == entity_id)
    rel_ids = {
        str(rel.get("rel_id"))
        for rel in relationships
        if entity_id in {str(rel.get("src_entity_id")), str(rel.get("dst_entity_id"))}
    }
    source_ids = set(clean_id_list(entity.get("source_ids")))
    for claim in claims:
        if str(claim.get("claim_id")) in claim_ids:
            source_ids.update(clean_id_list(claim.get("source_ids")))
    return {
        "entity_id": entity_id,
        "source_ids": sorted(source_ids),
        "claim_ids": sorted(item for item in claim_ids if item),
        "event_ids": sorted(item for item in event_ids if item),
        "relationship_ids": sorted(item for item in rel_ids if item),
        "privacy_level": entity.get("privacy_level"),
        "living_status": entity.get("living_status"),
        "public_export": entity.get("public_export", True),
    }


def append_identity_candidate(
    candidates: list[dict[str, Any]],
    *,
    reason: str,
    key: str,
    rows: list[tuple[int, dict[str, Any]]],
    context_by_id: dict[str, dict[str, Any]],
) -> None:
    if len(rows) < 2:
        return
    entity_ids = [str(row.get("entity_id")) for _idx, row in rows if row.get("entity_id")]
    contexts = [context_by_id.get(entity_id, {}) for entity_id in entity_ids]
    source_sets = [set(clean_id_list(context.get("source_ids"))) for context in contexts]
    shared_sources = sorted(set.intersection(*source_sets)) if source_sets else []
    private_flags = sorted(
        {
            str(context.get("privacy_level"))
            for context in contexts
            if context.get("privacy_level") in {"private_person", "minor", "unknown"}
        }
    )
    candidates.append(
        {
            "candidate_id": stable_id("IR", reason, key, "|".join(sorted(entity_ids))),
            "reason": reason,
            "match_key": key,
            "recommendation": "human_review_required_before_merge",
            "confidence": 0.65 if shared_sources else 0.5,
            "shared_source_ids": shared_sources,
            "privacy_flags": private_flags,
            "records": [compact_record("entities", row, idx) for idx, row in rows],
            "contexts": contexts,
        }
    )


def resolve_identities(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    entities, claims, events, relationships, event_links = _load_records(args.case_dir)
    context_by_id = _entity_contexts(entities, claims, events, relationships, event_links)
    candidates = _candidates(entities, context_by_id, args.min_key_chars, getattr(args, "include_merged", False))
    report = {
        "generated_at": now_utc(),
        "case_dir": str(case_path(args.case_dir)),
        "summary": {
            "candidate_count": len(candidates),
            "entity_count": len(entities),
            "policy": "This report does not merge, delete, or publicly identify entities.",
        },
        "candidates": candidates,
    }
    out = report_out_path(args.case_dir, getattr(args, "out", None), f"staging/candidates/identity_resolution_{today()}.json")
    write_json(out, report)
    log_action(args.case_dir, "resolve_identities", {"candidate_count": len(candidates), "report": str(out), "include_merged": getattr(args, "include_merged", False)})
    print(json.dumps({"candidate_count": len(candidates), "report": str(out)}, indent=2, ensure_ascii=False))


def _load_records(case_dir: str) -> tuple[list[dict[str, Any]], ...]:
    return tuple(read_jsonl(record_path(case_dir, name)) for name in ("entities", "claims", "events", "relationships", "event_links"))


def _entity_contexts(
    entities: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    events: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    event_links: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        str(entity.get("entity_id")): entity_resolution_context(
            entity,
            claims=claims,
            events=events,
            relationships=relationships,
            event_links=event_links,
        )
        for entity in entities
        if entity.get("entity_id")
    }


def _candidates(entities: list[dict[str, Any]], context_by_id: dict[str, dict[str, Any]], min_key_chars: int, include_merged: bool) -> list[dict[str, Any]]:
    groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for idx, entity in enumerate(entities, start=1):
        if entity.get("status") == "merged" and not include_merged:
            continue
        values = [entity.get("name"), entity.get("display_name"), *(entity.get("aliases", []) or [])]
        for value in values:
            key = normalize_match_text(value)
            if len(key) >= min_key_chars:
                groups.setdefault(key, []).append((idx, entity))
    candidates: list[dict[str, Any]] = []
    seen_entity_sets: set[tuple[str, ...]] = set()
    for key, rows in sorted(groups.items()):
        ids = tuple(sorted(str(row.get("entity_id")) for _idx, row in rows if row.get("entity_id")))
        if len(ids) < 2 or ids in seen_entity_sets:
            continue
        seen_entity_sets.add(ids)
        append_identity_candidate(candidates, reason="same_normalized_name_or_alias", key=key, rows=rows, context_by_id=context_by_id)
    return candidates
