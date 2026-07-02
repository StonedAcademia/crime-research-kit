import pytest

from adapters.ops.safety.policy import (
    PolicyError,
    apply_automation_defaults,
    ensure_staged_write,
    filter_public,
    lint_guilt_labels,
)


def test_staged_write_allows_staging_and_exports(synthetic_case_copy):
    ensure_staged_write(synthetic_case_copy, synthetic_case_copy / "staging" / "extractions" / "p.json")
    ensure_staged_write(synthetic_case_copy, synthetic_case_copy / "exports" / "evidence_board.md")


def test_staged_write_rejects_canonical_records(synthetic_case_copy):
    with pytest.raises(PolicyError):
        ensure_staged_write(synthetic_case_copy, synthetic_case_copy / "records" / "claims.jsonl")


def test_staged_write_rejects_escape_from_case(synthetic_case_copy):
    with pytest.raises(PolicyError):
        ensure_staged_write(synthetic_case_copy, synthetic_case_copy / "staging" / ".." / ".." / "elsewhere.json")


def test_filter_public_drops_private_records_by_default():
    records = [
        {"claim_id": "C1", "public_export": False},
        {"claim_id": "C2", "public_export": True},
        {"claim_id": "C3"},
    ]

    public = filter_public(records)
    internal = filter_public(records, include_private=True)

    assert [r["claim_id"] for r in public] == ["C2", "C3"]
    assert len(internal) == 3


def test_automation_defaults_force_unverified_private_low_confidence():
    record = apply_automation_defaults(
        {"claim_id": "C1", "status": "corroborated", "confidence": 0.9, "public_export": True}
    )

    assert record["status"] == "unverified"
    assert record["confidence"] <= 0.3
    assert record["public_export"] is False


def test_automation_defaults_fill_missing_confidence():
    record = apply_automation_defaults({"claim_id": "C1"})

    assert record["confidence"] == 0.2


def test_guilt_label_without_citation_is_flagged():
    packet = {"entities": [{"name": "A Person", "role": "suspect"}]}

    problems = lint_guilt_labels(packet)

    assert len(problems) == 1
    assert "suspect" in problems[0]
    assert "label_source_ids" in problems[0]


def test_guilt_label_with_citation_passes():
    packet = {"entities": [{"name": "A Person", "role": "suspect", "label_source_ids": ["S1"]}]}

    assert lint_guilt_labels(packet) == []


def test_neutral_labels_pass():
    packet = {"entities": [{"name": "A Person", "role": "witness"}, {"name": "B", "role": "former_member"}]}

    assert lint_guilt_labels(packet) == []
