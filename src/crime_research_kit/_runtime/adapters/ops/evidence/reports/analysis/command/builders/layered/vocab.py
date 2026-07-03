"""Shared layered graph vocabulary, pack-backed."""

from __future__ import annotations

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.vocabulary import VocabPacks, load_default_packs


def layer_order_map(packs: VocabPacks | None = None) -> dict[str, int]:
    return dict((packs or load_default_packs()).layer_order)
