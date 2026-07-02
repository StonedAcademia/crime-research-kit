import shutil
from pathlib import Path

import pytest

from tests.helpers import KIT_ROOT

TEST_CATEGORIES = frozenset({"unit", "integration", "e2e", "governance", "smoke"})


@pytest.fixture
def synthetic_case_copy(tmp_path: Path) -> Path:
    case_dir = tmp_path / "synthetic_case"
    shutil.copytree(KIT_ROOT / "data" / "examples" / "synthetic_case", case_dir)
    return case_dir


def pytest_collection_modifyitems(config, items):
    for item in items:
        path = Path(str(item.fspath)).resolve()
        try:
            category = path.relative_to(KIT_ROOT / "tests").parts[0]
        except ValueError:
            continue
        if category in TEST_CATEGORIES:
            item.add_marker(category)
