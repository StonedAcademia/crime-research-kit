import sys
from pathlib import Path

from case_builder.ops.runner import TrcrRunner
from tests.helpers import KIT_ROOT

REPO_ROOT = KIT_ROOT


def test_dry_run_returns_planned_command_without_executing():
    runner = TrcrRunner(repo_root=REPO_ROOT, dry_run=True)

    result = runner.run("validate", ["validate", "data/cases/nonexistent"])

    assert result.ok is True
    assert result.dry_run is True
    assert result.command[0] == sys.executable
    assert result.command[1].endswith("scripts/tcr.py")
    assert result.command[2:] == ["validate", "data/cases/nonexistent"]


def test_executed_run_validates_synthetic_case(synthetic_case_copy):
    runner = TrcrRunner(repo_root=REPO_ROOT, dry_run=False)

    result = runner.run("validate", ["validate", str(synthetic_case_copy)])

    assert result.ok is True
    assert result.returncode == 0
    assert result.dry_run is False


def test_failed_run_reports_error(tmp_path):
    runner = TrcrRunner(repo_root=REPO_ROOT, dry_run=False)

    result = runner.run("validate", ["validate", str(tmp_path / "not_a_case")])

    assert result.ok is False
    assert result.returncode != 0
    assert result.errors


def test_runner_finds_tcr_script():
    runner = TrcrRunner(repo_root=REPO_ROOT)

    assert runner.tcr_path.exists()
