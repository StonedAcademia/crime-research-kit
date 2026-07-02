"""Matching helpers for private name-list co-mention links."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from core.casefile import append_jsonl, case_path, record_path, stable_id

from .parsing import normalize_lookup


def entity_lookup_keys(entity: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for field in ("name", "display_name"):
        keys.update(normalize_lookup(entity.get(field)))
    for alias in entity.get("aliases", []) or []:
        keys.update(normalize_lookup(str(alias)))
    return keys


def build_entity_index(entities: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for entity in entities:
        for key in entity_lookup_keys(entity):
            index.setdefault(key, entity)
    return index


def find_entity_for_entry(entry: dict[str, Any], index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    for alias in entry["aliases"]:
        for key in normalize_lookup(alias):
            if key in index:
                return index[key]
    return None


def contains_name(text: str, name: str) -> bool:
    clean = name.strip()
    return bool(clean and re.search(rf"(?<!\w){re.escape(clean)}(?!\w)", text, flags=re.I))


def read_source_texts(case_dir: str | Path, sources: list[dict[str, Any]]) -> dict[str, str]:
    cdir = case_path(case_dir)
    texts: dict[str, str] = {}
    for source in sources:
        source_id = source.get("source_id")
        text_rel = source.get("text_path")
        if not source_id or not text_rel:
            continue
        path = cdir / str(text_rel)
        if path.exists():
            texts[str(source_id)] = path.read_text(encoding="utf-8", errors="replace")
    return texts


def source_matches_for_entry(entry: dict[str, Any], source_texts: dict[str, str]) -> set[str]:
    return {
        source_id
        for source_id, text in source_texts.items()
        if any(contains_name(text, alias) for alias in entry["aliases"])
    }


def make_candidate_entity(entry: dict[str, Any], source_ids: Iterable[str]) -> dict[str, Any]:
    return {
        "entity_id": stable_id("E", entry["primary"], "name_list_candidate"),
        "entity_type": "person",
        "name": entry["primary"],
        "display_name": entry["primary"],
        "aliases": entry["aliases"][1:],
        "status": "candidate",
        "role_tags": ["person_mentioned"],
        "privacy_level": "unknown",
        "living_status": "unknown",
        "source_ids": sorted(set(source_ids)),
        "claim_ids": [],
        "public_export": False,
        "notes": (
            "Candidate created from user-provided name list by link-names. "
            "Do not treat as identified or publicly export until source-reviewed."
        ),
    }


def refresh_entity_from_name_entry(entity: dict[str, Any], entry: dict[str, Any], source_ids: Iterable[str]) -> bool:
    changed = False
    existing_sources = clean_id_list(entity.get("source_ids"))
    merged_sources = sorted(set(existing_sources) | set(source_ids))
    if merged_sources != existing_sources:
        entity["source_ids"] = merged_sources
        changed = True
    aliases = list(entity.get("aliases", []) or [])
    alias_keys = {str(alias).casefold() for alias in aliases}
    entity_name_keys = {str(entity[field]).casefold() for field in ("name", "display_name") if entity.get(field)}
    for alias in entry["aliases"]:
        alias_key = alias.casefold()
        if alias_key in entity_name_keys or alias_key in alias_keys:
            continue
        aliases.append(alias)
        alias_keys.add(alias_key)
        changed = True
    if aliases != (entity.get("aliases", []) or []):
        entity["aliases"] = aliases
    return changed


def append_if_new(case_dir: str | Path, record_name: str, row: dict[str, Any], id_field: str, existing_ids: set[str]) -> bool:
    row_id = str(row.get(id_field, ""))
    if not row_id or row_id in existing_ids:
        return False
    append_jsonl(record_path(case_dir, record_name), row)
    existing_ids.add(row_id)
    return True


def clean_id_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item not in (None, "")]


def pair_ids(left: str, right: str) -> tuple[str, str]:
    ordered = sorted([left, right])
    return ordered[0], ordered[1]


def co_mention_note(anchor: str) -> str:
    return (
        f"Name-list co-mention via {anchor}. This does not establish guilt, "
        "membership, motive, direct participation, or a source-stated relationship."
    )
