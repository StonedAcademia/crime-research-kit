"""Vocabulary pack loading, matching, and per-case override merging."""

from __future__ import annotations

import json

import pytest

from adapters.ops.evidence.reports.analysis.vocabulary import (
    CASE_PACK_FILENAME,
    TermPack,
    load_case_packs,
    load_default_packs,
    match_pack,
)
from core.casefile import CasefileError


def test_default_packs_load_from_registry():
    packs = load_default_packs()
    class_keys = [pack.key for pack in packs.relationship_classes]
    assert class_keys[0] == "documented_successor"
    assert "personnel_bridge" in class_keys
    assert packs.layer_order["person"] == 1
    assert packs.status_scores["verified"] == 1.0
    assert packs.grade_scores["X"] == 0.0


def test_defaults_contain_no_case_specific_terms():
    packs = load_default_packs()
    all_terms = " ".join(
        term
        for pack in packs.relationship_classes + packs.relation_families + packs.bridge_labels
        for term in pack.terms
    )
    for banned in ("promis", "inslaw", "jonestown", "narconon", "monarch", "montauk", "hubbard", "finders"):
        assert banned not in all_terms


def test_match_pack_first_match_wins():
    packs = [TermPack(key="a", terms=["alpha"]), TermPack(key="b", terms=["alpha", "beta"])]
    assert match_pack("has alpha inside", packs) == "a"
    assert match_pack("only beta here", packs) == "b"
    assert match_pack("nothing", packs) is None


def test_case_override_extends_and_prepends(tmp_path):
    (tmp_path / "case.json").write_text(json.dumps({"case_id": "t"}), encoding="utf-8")
    override = {
        "relationship_classes": [
            {"key": "contested_overlap", "terms": ["housecat_inquiry"]},
            {"key": "software_inquiry_context", "terms": ["promiscase"]},
        ],
        "layer_order": {"person": 99},
    }
    (tmp_path / CASE_PACK_FILENAME).write_text(json.dumps(override), encoding="utf-8")
    packs = load_case_packs(tmp_path)
    keys = [pack.key for pack in packs.relationship_classes]
    assert keys[0] == "software_inquiry_context"
    contested = next(pack for pack in packs.relationship_classes if pack.key == "contested_overlap")
    assert "housecat_inquiry" in contested.terms
    assert "contested" in contested.terms
    assert packs.layer_order["person"] == 99
    assert packs.layer_order["institution"] == 2
    assert load_default_packs().layer_order["person"] == 1


def test_missing_override_returns_defaults(tmp_path):
    (tmp_path / "case.json").write_text(json.dumps({"case_id": "t"}), encoding="utf-8")
    assert load_case_packs(tmp_path).layer_order["person"] == 1


def test_malformed_override_fails_fast(tmp_path):
    (tmp_path / "case.json").write_text(json.dumps({"case_id": "t"}), encoding="utf-8")
    (tmp_path / CASE_PACK_FILENAME).write_text("{not json", encoding="utf-8")
    with pytest.raises(CasefileError) as excinfo:
        load_case_packs(tmp_path)
    assert CASE_PACK_FILENAME in str(excinfo.value)
