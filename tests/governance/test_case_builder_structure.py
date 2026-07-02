from pathlib import Path

from tests.helpers import KIT_ROOT

CASE_BUILDER_ROOT = KIT_ROOT / "src" / "case_builder"
MAX_NON_COMMENT_LOC = 200


def non_comment_loc(path: Path) -> int:
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        count += 1
    return count


def package_dirs() -> list[Path]:
    nested = [path for path in CASE_BUILDER_ROOT.rglob("*") if path.is_dir() and (path / "__init__.py").exists()]
    return [CASE_BUILDER_ROOT, *sorted(nested)]


def test_case_builder_package_dirs_have_inline_readmes():
    missing = [path.relative_to(KIT_ROOT).as_posix() for path in package_dirs() if not (path / "README.md").exists()]

    assert missing == []


def test_case_builder_modules_stay_under_200_non_comment_loc():
    offenders = {
        path.relative_to(KIT_ROOT).as_posix(): non_comment_loc(path)
        for path in CASE_BUILDER_ROOT.rglob("*.py")
        if non_comment_loc(path) > MAX_NON_COMMENT_LOC
    }

    assert offenders == {}
