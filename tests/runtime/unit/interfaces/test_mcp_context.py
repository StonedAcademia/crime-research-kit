from pathlib import Path

import pytest

from adapters.interfaces.mcp.context import (
    ServerContext,
    default_skill_root,
    error_dict,
    list_case_slugs,
    resolve_case,
)
from adapters.ops.runner import CrkRunner
from tests.helpers import KIT_ROOT


def make_ctx(cases_root: Path) -> ServerContext:
    return ServerContext(
        repo_root=KIT_ROOT,
        cases_root=cases_root,
        runner=CrkRunner(repo_root=KIT_ROOT, dry_run=True),
    )


def test_resolve_case_returns_case_path(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    resolved = resolve_case(ctx, "synthetic_case")

    assert resolved == str(synthetic_case_copy)


def test_resolve_case_rejects_traversal_and_unknown(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    for bad in ("../etc", "a/b", "", ".hidden", "no_such_case"):
        with pytest.raises(ValueError):
            resolve_case(ctx, bad)


def test_resolve_case_rejects_symlink_escape(tmp_path):
    cases_root = tmp_path / "cases"
    outside = tmp_path / "outside"
    cases_root.mkdir()
    outside.mkdir()
    (outside / "case.json").write_text("{}", encoding="utf-8")
    (cases_root / "escaped").symlink_to(outside, target_is_directory=True)
    ctx = make_ctx(cases_root)

    with pytest.raises(ValueError):
        resolve_case(ctx, "escaped")


def test_list_case_slugs_finds_only_cases(synthetic_case_copy):
    (synthetic_case_copy.parent / "not_a_case").mkdir()
    ctx = make_ctx(synthetic_case_copy.parent)

    assert list_case_slugs(ctx) == ["synthetic_case"]


def test_default_skill_root_points_at_repo_local_skill():
    assert (default_skill_root(KIT_ROOT) / "SKILL.md").exists()


def test_error_dict_shape():
    assert error_dict("boom") == {"ok": False, "errors": ["boom"]}
