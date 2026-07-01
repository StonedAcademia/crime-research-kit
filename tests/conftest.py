import shutil
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def synthetic_case_copy(tmp_path: Path) -> Path:
    case_dir = tmp_path / "synthetic_case"
    shutil.copytree(KIT_ROOT / "data" / "examples" / "synthetic_case", case_dir)
    return case_dir
