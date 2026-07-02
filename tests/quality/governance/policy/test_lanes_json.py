import re
import subprocess
import sys

from case_builder.core.lanes.registry import load_lanes
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


def test_tcr_draft_extraction_help_includes_registry_templates():
    registry = load_registry()

    result = subprocess.run(
        [
            sys.executable,
            ".agents/skills/truecrime-cult-research/scripts/tcr.py",
            "draft-extraction",
            "--help",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    for template_id in registry["templates"]:
        assert template_id in result.stdout


def test_tcr_plan_public_records_help_includes_planning_lanes():
    registry = load_registry()
    planning_lanes = {
        lane_id for lane_id, lane in registry["lanes"].items() if lane["public_record_plan"]
    }

    result = subprocess.run(
        [
            sys.executable,
            ".agents/skills/truecrime-cult-research/scripts/tcr.py",
            "plan-public-records",
            "--help",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    for lane_id in planning_lanes:
        assert lane_id in result.stdout
    assert "narrative-readiness" not in result.stdout
