import re

from case_builder.lanes.registry import load_lanes
from tests.helpers import KIT_ROOT as ROOT

SKILLS_ROOT = ROOT / ".agents" / "skills"
MAIN_SKILL = SKILLS_ROOT / "truecrime-cult-research" / "SKILL.md"


def load_registry() -> dict:
    return load_lanes(ROOT / "docs" / "registry")


def test_main_skill_documents_tool_access():
    text = MAIN_SKILL.read_text(encoding="utf-8")

    assert "## Tool access" in text
    assert "crk-mcp" in text
    assert "import_extraction(confirm=true)" in text
    assert "docs/registry/" in text


def test_lane_skill_docs_reference_registry_and_templates():
    registry = load_registry()

    for lane_id, lane in registry["lanes"].items():
        skill_doc = SKILLS_ROOT / lane["skill"] / "SKILL.md"
        if not skill_doc.exists():
            continue
        text = skill_doc.read_text(encoding="utf-8")
        assert "docs/registry/" in text, lane_id
        assert f"template `{lane['template']}`" in text or f"--template {lane['template']}" in text, lane_id


def test_skill_docs_only_reference_known_template_and_lane_ids():
    registry = load_registry()
    known_templates = set(registry["templates"])
    known_lanes = set(registry["lanes"])

    for skill_doc in SKILLS_ROOT.glob("*/SKILL.md"):
        text = skill_doc.read_text(encoding="utf-8")
        for template_id in re.findall(r"--template\s+([a-z0-9-]+)", text):
            assert template_id in known_templates, f"{skill_doc}: {template_id}"
        for lane_id in re.findall(r"--lane\s+([a-z0-9-]+)", text):
            assert lane_id in known_lanes, f"{skill_doc}: {lane_id}"
