"""Registry-backed vocabulary packs for analysis classification."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from core.casefile import CasefileError, case_path
from core.lanes.registry import default_lanes_path

CASE_PACK_FILENAME = "analysis_vocabulary.json"


class TermPack(BaseModel):
    key: str
    terms: list[str]


class VocabPacks(BaseModel):
    version: int = 1
    relation_families: list[TermPack] = Field(default_factory=list)
    relationship_classes: list[TermPack] = Field(default_factory=list)
    bridge_labels: list[TermPack] = Field(default_factory=list)
    layer_order: dict[str, int] = Field(default_factory=dict)
    status_scores: dict[str, float] = Field(default_factory=dict)
    grade_scores: dict[str, float] = Field(default_factory=dict)


def match_pack(text: str, packs: list[TermPack]) -> str | None:
    for pack in packs:
        if any(term in text for term in pack.terms):
            return pack.key
    return None


def load_default_packs() -> VocabPacks:
    return _default_packs().model_copy(deep=True)


def load_case_packs(case_dir: str | Path) -> VocabPacks:
    packs = load_default_packs()
    override_path = case_path(case_dir) / CASE_PACK_FILENAME
    if not override_path.exists():
        return packs
    try:
        raw = json.loads(override_path.read_text(encoding="utf-8"))
        override = VocabPacks.model_validate(raw)
    except Exception as exc:
        raise CasefileError(f"Malformed {CASE_PACK_FILENAME} in {case_path(case_dir)}: {exc}") from exc
    packs.relation_families = _merge_packs(packs.relation_families, override.relation_families)
    packs.relationship_classes = _merge_packs(packs.relationship_classes, override.relationship_classes)
    packs.bridge_labels = _merge_packs(packs.bridge_labels, override.bridge_labels)
    packs.layer_order.update(override.layer_order)
    packs.status_scores.update(override.status_scores)
    packs.grade_scores.update(override.grade_scores)
    return packs


@lru_cache(maxsize=1)
def _default_packs() -> VocabPacks:
    payload = {**_read_registry_json("vocabulary.json"), **_read_registry_json("scoring.json")}
    return VocabPacks.model_validate(payload)


def _read_registry_json(name: str) -> dict[str, Any]:
    root = default_lanes_path()
    analysis_dir = root / "analysis" if isinstance(root, Path) else root.joinpath("analysis")
    return json.loads(analysis_dir.joinpath(name).read_text(encoding="utf-8"))


def _merge_packs(base: list[TermPack], overrides: list[TermPack]) -> list[TermPack]:
    merged = {pack.key: pack for pack in base}
    prepended: list[TermPack] = []
    for override in overrides:
        if override.key in merged:
            merged[override.key].terms = _extend_terms(merged[override.key].terms, override.terms)
        else:
            prepended.append(override)
    return [*prepended, *(merged[pack.key] for pack in base)]


def _extend_terms(base: list[str], extra: list[str]) -> list[str]:
    seen = set(base)
    out = list(base)
    for term in extra:
        if term in seen:
            continue
        seen.add(term)
        out.append(term)
    return out
