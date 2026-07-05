import pytest

from crime_research_kit._runtime.adapters.ops.safety.policy import (
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


ADDRESS_MATCHES = [
    "123 Main Street",
    "1307 4th St NE",
    "5 Elm Dr",
    "1600 Pennsylvania Ave NW",
    "500 Fifth Ave New York",
    "10 Downing St, London",
    "45 Martin Luther King Jr Blvd",
]

ADDRESS_NON_MATCHES = [
    # A number in prose followed by a title must not read as a street address:
    "the CIA approved a $60,000 grant to Dr. Ewen Cameron, a world-renowned psychiatrist",
    "12 people met Dr. Cameron at the clinic",
    "Building 5, Dr. Smith's office",
    "St. John's Hospital admitted 40 patients",
    "Subproject 68 cost $59,267.54 in total",
    "Dr. Ewen Cameron developed psychic driving",
]


@pytest.mark.parametrize("text", ADDRESS_MATCHES)
def test_address_regex_matches_real_addresses(text):
    from crime_research_kit._runtime.adapters.ops.evidence.quality.safety.public_export import ADDRESS_RE

    assert ADDRESS_RE.search(text), f"expected an address match in {text!r}"


@pytest.mark.parametrize("text", ADDRESS_NON_MATCHES)
def test_address_regex_ignores_title_and_currency_prose(text):
    from crime_research_kit._runtime.adapters.ops.evidence.quality.safety.public_export import ADDRESS_RE

    assert not ADDRESS_RE.search(text), f"false positive: {text!r} should not read as an address"


ALLEGATION_MATCHES = [
    "he was charged with murder",
    "charged in the death of the researcher",
    "criminal charges were filed",
    "accused of abuse",
    "alleged assault",
]

ALLEGATION_NON_MATCHES = [
    # Accounting uses of "charged" are not allegations:
    "the cost was charged to a TSD accounting allotment",
    "the amount was charged against the account",
    "$5,000 charged off to overhead",
]


@pytest.mark.parametrize("text", ALLEGATION_MATCHES)
def test_allegation_regex_matches_criminal_language(text):
    from crime_research_kit._runtime.adapters.ops.evidence.quality.safety.public_export import ALLEGATION_RE

    assert ALLEGATION_RE.search(text), f"expected an allegation match in {text!r}"


@pytest.mark.parametrize("text", ALLEGATION_NON_MATCHES)
def test_allegation_regex_ignores_accounting_charged(text):
    from crime_research_kit._runtime.adapters.ops.evidence.quality.safety.public_export import ALLEGATION_RE

    assert not ALLEGATION_RE.search(text), f"false positive: {text!r} should not read as an allegation"
