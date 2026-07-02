import json
from pathlib import Path

from tests.helpers import KIT_ROOT


def test_schemas_parse():
    for path in (KIT_ROOT / "docs" / "schemas").glob("*.schema.json"):
        json.loads(path.read_text())


def test_skill_exists():
    assert (KIT_ROOT / ".agents/skills/truecrime-cult-research/SKILL.md").exists()
