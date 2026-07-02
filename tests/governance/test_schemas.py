import json
from pathlib import Path

from tests.helpers import KIT_ROOT


def test_schemas_parse():
    schema_paths = [
        *(KIT_ROOT / "docs" / "schemas").rglob("*.schema.json"),
        *(KIT_ROOT / "docs" / "registry").glob("*.schema.json"),
    ]
    for path in schema_paths:
        json.loads(path.read_text())


def test_skill_exists():
    assert (KIT_ROOT / ".agents/skills/truecrime-cult-research/SKILL.md").exists()
