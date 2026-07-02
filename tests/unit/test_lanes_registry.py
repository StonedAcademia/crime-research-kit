import json
from pathlib import Path

import pytest

from case_builder.lanes import registry as lanes_registry
from tests.helpers import KIT_ROOT

ROOT = KIT_ROOT


def load_json() -> dict:
    return json.loads((ROOT / "docs" / "lanes.json").read_text(encoding="utf-8"))


def test_default_lanes_path_resolves_from_repo_root():
    assert lanes_registry.default_lanes_path(ROOT) == ROOT / "docs" / "lanes.json"


def test_fallback_lists_match_registry():
    registry = load_json()

    assert lanes_registry.fallback_source_lanes() == registry["fallback_source_lanes"]
    assert lanes_registry.fallback_public_record_lanes() == registry["fallback_public_record_lanes"]


def test_lane_triggers_use_inference_set():
    triggers = lanes_registry.lane_triggers()

    assert "legal-court" in triggers
    assert "identity-resolution" not in triggers
    assert all(isinstance(values, tuple) for values in triggers.values())


def test_infer_lanes_matches_multiple_terms():
    lanes = lanes_registry.infer_lanes("missing person court filing")

    assert "missing-persons" in lanes
    assert "legal-court" in lanes


def test_explicit_lanes_are_deduped_without_validation():
    assert lanes_registry.infer_lanes("ignored", ["foo", "foo", "legal-court"]) == ["foo", "legal-court"]


def test_public_record_plan_includes_registry_metadata():
    plan = lanes_registry.public_record_plan("legal-court", "Jane Doe")

    assert plan["lane"] == "legal-court"
    assert plan["skill"] == "legal-court-records"
    assert plan["template"] == "legal-court"
    assert plan["source_types"]
    assert plan["notes"]
    assert plan["suggested_queries"][0].startswith('"Jane Doe"')


def test_public_record_plan_rejects_non_planning_lane():
    with pytest.raises(ValueError):
        lanes_registry.public_record_plan("narrative-readiness", "Jane Doe")


def test_source_lanes_exports_match_registry():
    from case_builder.agents import source_lanes

    assert source_lanes.FALLBACK_LANES == lanes_registry.fallback_source_lanes()
    assert source_lanes.LANE_TRIGGERS == lanes_registry.lane_triggers()
