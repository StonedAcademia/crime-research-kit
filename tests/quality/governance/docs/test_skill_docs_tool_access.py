import json
import re
from collections import defaultdict
from pathlib import Path

from core.lanes.registry import load_lanes
from tests.helpers import KIT_ROOT as ROOT

SKILLS_ROOT = ROOT / ".agents" / "skills"
MAIN_SKILL = SKILLS_ROOT / "truecrime-cult-research" / "SKILL.md"
SKILL_CATALOG = SKILLS_ROOT / "catalog.json"


def load_registry() -> dict:
    return load_lanes(ROOT / "docs" / "registry")


def load_catalog() -> dict:
    return json.loads(SKILL_CATALOG.read_text(encoding="utf-8"))


def skill_dirs() -> set[str]:
    return {
        path.name
        for path in SKILLS_ROOT.iterdir()
        if path.is_dir() and (path / "SKILL.md").exists()
    }


def frontmatter_fields(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines and lines[0] == "---", path
    end = lines[1:].index("---") + 1
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields


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


def test_skill_catalog_covers_flat_skill_tree():
    catalog = load_catalog()
    grouped_skills = [skill for group in catalog["groups"] for skill in group["skills"]]

    assert catalog["layout"] == "flat"
    assert sorted(catalog["skills"]) == sorted(skill_dirs())
    assert sorted(grouped_skills) == sorted(skill_dirs())
    assert len(grouped_skills) == len(set(grouped_skills))

    for group in catalog["groups"]:
        for skill in group["skills"]:
            assert catalog["skills"][skill]["group"] == group["id"]


def test_skill_catalog_matches_lane_registry():
    registry = load_registry()
    catalog = load_catalog()
    lanes_by_skill: dict[str, list[str]] = defaultdict(list)
    templates_by_skill: dict[str, set[str]] = defaultdict(set)
    for lane_id, lane in registry["lanes"].items():
        lanes_by_skill[lane["skill"]].append(lane_id)
        templates_by_skill[lane["skill"]].add(lane["template"])

    for skill, row in catalog["skills"].items():
        expected_lanes = sorted(lanes_by_skill.get(skill, []))
        assert row["registry_lanes"] == expected_lanes, skill
        if expected_lanes:
            assert row["templates"] == sorted(templates_by_skill[skill]), skill

    assert catalog["skills"]["truecrime-cult-research"]["templates"] == sorted(registry["templates"])


def test_skill_metadata_files_are_present_and_named():
    for skill in skill_dirs():
        fields = frontmatter_fields(SKILLS_ROOT / skill / "SKILL.md")
        openai_yaml = SKILLS_ROOT / skill / "agents" / "openai.yaml"
        interface_text = openai_yaml.read_text(encoding="utf-8")

        assert fields["name"] == skill
        assert isinstance(fields["description"], str)
        assert fields["description"]
        assert "display_name:" in interface_text
        assert "short_description:" in interface_text
        assert "default_prompt:" in interface_text


def test_skill_catalog_references_existing_resources():
    catalog = load_catalog()
    for skill, row in catalog["skills"].items():
        root = SKILLS_ROOT / skill
        for reference in row.get("references", []):
            assert (root / "references" / reference).exists(), f"{skill}: {reference}"
        for script in row.get("scripts", []):
            assert (root / "scripts" / script).exists(), f"{skill}: {script}"
        for asset in row.get("assets", []):
            assert (root / "assets" / asset).exists(), f"{skill}: {asset}"
