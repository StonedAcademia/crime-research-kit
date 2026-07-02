"""The synthetic case's override pack changes classification end to end."""

from __future__ import annotations

from pathlib import Path

from adapters.ops.evidence.reports.analysis.relationships import relationship_class
from adapters.ops.evidence.reports.analysis.vocabulary import load_case_packs, load_default_packs

SYNTHETIC_CASE = Path(__file__).resolve().parents[5] / "data" / "examples" / "synthetic_case"


def test_synthetic_override_loads_and_prepends_case_packs():
    packs = load_case_packs(SYNTHETIC_CASE)
    family_keys = [pack.key for pack in packs.relation_families]
    assert family_keys[0] == "software_inquiry_context"
    assert "software_inquiry_context" not in [pack.key for pack in load_default_packs().relation_families]


def test_case_specific_term_classifies_only_with_override():
    record = {
        "rel_id": "r1",
        "relation_type": "linked_via_narconon_program_history",
        "status": "corroborated",
        "notes": "narconon",
    }
    assert relationship_class(record) == "unclassified"
    assert relationship_class(record, packs=load_case_packs(SYNTHETIC_CASE)) == "method_diffusion"
