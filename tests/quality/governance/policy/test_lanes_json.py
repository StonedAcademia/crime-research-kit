import json
import re

from crime_research_kit._runtime.adapters.interfaces.cli.app import build_click_command
from crime_research_kit._runtime.core.lanes.registry import load_lanes
from tests.helpers import KIT_ROOT

ROOT = KIT_ROOT
REGISTRY_ROOT = ROOT / "docs" / "registry"
TEMPLATES_ROOT = ROOT / ".agents" / "skills" / "truecrime-cult-research" / "assets" / "templates"
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]*")


def load_registry() -> dict:
    return load_lanes(REGISTRY_ROOT)


def test_lanes_json_exists_and_has_version():
    registry = load_registry()

    assert (REGISTRY_ROOT / "index.json").exists()
    assert not (REGISTRY_ROOT / "lanes.json").exists()
    assert registry["version"] == 1
    assert isinstance(registry["lanes"], dict)
    assert isinstance(registry["templates"], dict)


def test_fallback_lanes_are_defined():
    registry = load_registry()
    lanes = set(registry["lanes"])

    assert set(registry["fallback_source_lanes"]) <= lanes
    assert set(registry["fallback_public_record_lanes"]) <= lanes


def test_lane_and_template_ids_are_slugs():
    registry = load_registry()

    for lane_id in registry["lanes"]:
        assert SLUG_RE.fullmatch(lane_id)
    for template_id in registry["templates"]:
        assert SLUG_RE.fullmatch(template_id)


def test_lane_templates_and_template_files_exist():
    registry = load_registry()
    templates = registry["templates"]

    for lane in registry["lanes"].values():
        assert lane["template"] in templates
    for template in templates.values():
        assert (TEMPLATES_ROOT / template["template_file"]).exists()


def test_public_record_lanes_have_required_metadata():
    registry = load_registry()

    for lane_id, lane in registry["lanes"].items():
        if not lane.get("public_record_plan"):
            continue
        assert lane.get("skill"), lane_id
        assert lane.get("triggers"), lane_id
        assert lane.get("source_types"), lane_id
        assert lane.get("notes"), lane_id


def test_generic_is_template_not_lane():
    registry = load_registry()

    assert "generic" in registry["templates"]
    assert "generic" not in registry["lanes"]


def option_choices(command: str, option: str) -> set[str]:
    for param in build_click_command().commands[command].params:
        if getattr(param, "param_type_name", None) == "option" and option in [*param.opts, *param.secondary_opts]:
            return set(getattr(param.type, "choices", None) or [])
    return set()


def test_ledger_draft_extraction_choices_include_registry_templates():
    registry = load_registry()
    choices = option_choices("draft-extraction", "--template")

    for template_id in registry["templates"]:
        assert template_id in choices


def test_ledger_plan_public_records_choices_include_planning_lanes():
    registry = load_registry()
    planning_lanes = {
        lane_id for lane_id, lane in registry["lanes"].items() if lane["public_record_plan"]
    }
    choices = option_choices("plan-public-records", "--lane")

    for lane_id in planning_lanes:
        assert lane_id in choices
    assert "narrative-readiness" not in choices


def test_analysis_vocabulary_shard_is_well_formed():
    payload = json.loads((REGISTRY_ROOT / "analysis" / "vocabulary.json").read_text(encoding="utf-8"))
    known_classes = {
        "documented_successor",
        "method_diffusion",
        "personnel_bridge",
        "narrative_inheritance",
        "contested_overlap",
        "hypothesis_requires_more_sources",
    }
    for section in ("relation_families", "relationship_classes", "bridge_labels"):
        for pack in payload[section]:
            assert isinstance(pack["key"], str) and pack["key"]
            assert pack["terms"] and all(isinstance(term, str) and term for term in pack["terms"])
    assert {pack["key"] for pack in payload["relationship_classes"]} <= known_classes
    assert set(payload["layer_order"]) >= {"person", "institution", "event"}


def test_analysis_scoring_shard_is_well_formed():
    payload = json.loads((REGISTRY_ROOT / "analysis" / "scoring.json").read_text(encoding="utf-8"))
    assert set(payload["status_scores"]) >= {"verified", "corroborated", "disputed", "unverified"}
    assert set(payload["grade_scores"]) == {"A", "B", "C", "D", "X"}
    for table in (payload["status_scores"], payload["grade_scores"]):
        assert all(0.0 <= value <= 1.0 for value in table.values())
