"""Vocabulary pack loading, matching, and per-case override merging."""

from __future__ import annotations

import json

import pytest

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.vocabulary import (
    CASE_PACK_FILENAME,
    TermPack,
    VocabPacks,
    load_case_packs,
    load_default_packs,
    match_pack,
)
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.relationships import relation_family, relationship_class
from crime_research_kit._runtime.core.casefile import CasefileError


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


def test_relationship_class_unmatched_falls_to_unclassified():
    record = {"rel_id": "r1", "relation_type": "vague_link", "status": "corroborated", "notes": ""}
    assert relationship_class(record) == "unclassified"


def test_relationship_class_structural_rules_survive_empty_packs():
    empty = VocabPacks()
    assert relationship_class({"relation_type": "co_mentioned_with"}, packs=empty) == "hypothesis_requires_more_sources"
    assert relationship_class({"relation_type": "x", "status": "disputed"}, packs=empty) == "contested_overlap"
    assert relationship_class({"relation_type": "x", "status": "unverified"}, packs=empty) == "hypothesis_requires_more_sources"
    assert relationship_class({"relation_type": "x"}, "event_link", packs=empty) == "personnel_bridge"


def test_relationship_class_respects_explicit_field():
    assert relationship_class({"relationship_class": "method_diffusion", "relation_type": "x"}) == "method_diffusion"


def test_relation_family_pack_driven_and_unclassified():
    assert relation_family("completed_treatment_at") == "treatment_lineage"
    assert relation_family("co_mentioned_with") == "lead_only_co_mentions"
    assert relation_family("x", "event_link") == "event_context"
    assert relation_family("totally_novel_relation") == "unclassified"


def test_case_pack_changes_classification(tmp_path):
    (tmp_path / "case.json").write_text(json.dumps({"case_id": "t"}), encoding="utf-8")
    (tmp_path / "analysis_vocabulary.json").write_text(
        json.dumps({"relationship_classes": [{"key": "contested_overlap", "terms": ["zzz_special_inquiry"]}]}),
        encoding="utf-8",
    )
    record = {
        "rel_id": "r1",
        "relation_type": "x",
        "notes": "zzz_special_inquiry raised",
        "status": "corroborated",
    }
    assert relationship_class(record) == "unclassified"
    assert relationship_class(record, packs=load_case_packs(tmp_path)) == "contested_overlap"


def test_status_and_grade_scores_come_from_packs():
    from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.classifiers import source_grade_score, status_score

    assert status_score("verified") == 1.0
    custom = VocabPacks(status_scores={"verified": 0.5}, grade_scores={"A": 0.1})
    assert status_score("verified", packs=custom) == 0.5
    assert source_grade_score([{"reliability_grade": "A"}], packs=custom) == 0.1


def test_layer_order_map_reads_packs():
    from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.layered.vocab import layer_order_map

    assert layer_order_map()["person"] == 1
    assert layer_order_map(VocabPacks(layer_order={"person": 42}))["person"] == 42


def test_classify_bridge_path_label_terms_from_packs():
    from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.paths import classify_bridge_path

    steps = [("a", "b", {"relation_type": "x", "status": "corroborated", "edge_type": "relationship"})]
    meta = {"a": {"label": "zeta widget hub"}, "b": {"label": "other"}}
    default = classify_bridge_path(steps, meta)
    assert default in {"direct_or_near_direct", "indirect_context_bridge", "unclassified_bridge"} or default.endswith(
        "_bridge"
    )
    custom = VocabPacks(bridge_labels=[TermPack(key="category_bridge", terms=["zeta widget hub"])])
    assert classify_bridge_path(steps, meta, packs=custom) == "category_bridge"
