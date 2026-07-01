import json
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = KIT_ROOT.parent


def test_schemas_parse():
    for path in (KIT_ROOT / "docs" / "schemas").glob("*.schema.json"):
        json.loads(path.read_text())


def test_skill_exists():
    assert (REPO_ROOT / ".agents/skills/truecrime-cult-research/SKILL.md").exists()
