"""Governance: GitHub workflows stay thin Moon callers and match branch gates."""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

from tests.helpers import KIT_ROOT, moon_task_names


WORKFLOWS = KIT_ROOT / ".github" / "workflows"


def workflow_run_commands() -> list[tuple[str, int, str]]:
    commands: list[tuple[str, int, str]] = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = re.match(r"\s*run:\s*(.+?)\s*$", line)
            if match:
                commands.append((path.name, lineno, match.group(1).strip("'\"")))
    return commands


def load_branch_gate():
    path = KIT_ROOT / "deployment" / "scripts" / "checks" / "branch_gate.py"
    spec = importlib.util.spec_from_file_location("branch_gate", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def target_name(arg: str) -> str:
    if ":" not in arg:
        return arg
    project, task = arg.split(":", 1)
    assert project == "crk", f"unexpected moon project: {arg}"
    return task


def test_workflow_run_steps_are_moon_targets():
    targets = moon_task_names()
    failures: list[str] = []
    for workflow, lineno, command in workflow_run_commands():
        parts = command.split()
        if parts[:2] != ["moon", "run"]:
            failures.append(f"{workflow}:{lineno} does not start with moon run: {command}")
            continue
        for target in parts[2:]:
            if target_name(target) not in targets:
                failures.append(f"{workflow}:{lineno} unknown moon target: {target}")
    assert not failures, "\n".join(failures)


def test_github_workflow_shape_budget():
    assert (KIT_ROOT / ".github").is_dir()
    assert len([path for path in (KIT_ROOT / ".github").iterdir() if path.is_file()]) <= 4
    assert len([path for path in (KIT_ROOT / ".github").iterdir() if path.is_dir()]) <= 3
    assert sorted(path.name for path in WORKFLOWS.glob("*.yml")) == ["audit.yml", "ci.yml", "release.yml"]


def test_branch_prefix_targets_are_resolved():
    gate = load_branch_gate()

    assert gate.targets_for(["docs/readme"]) == ["crk:check", "crk:test-governance"]
    assert gate.targets_for(["gov/example"]) == ["crk:check", "crk:test-governance", "crk:test-smoke"]
    assert gate.targets_for(["ci/workflows"]) == [
        "crk:check",
        "crk:test-governance",
        "crk:test-smoke",
        "crk:test-integration",
    ]
    assert gate.targets_for(["experiment/foo"]) == ["crk:check", "crk:test"]


def test_branch_gate_dry_run_prints_resolved_targets():
    env = {**os.environ, "CRK_HOOK_BRANCH": "ci/workflows"}
    proc = subprocess.run(
        [sys.executable, "deployment/scripts/checks/branch_gate.py", "--dry-run"],
        cwd=KIT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "crk:test-integration" in proc.stdout


def test_cli_surface_matches_snapshot():
    import json

    from crime_research_kit._runtime.adapters.interfaces.cli.app import build_click_command
    from crime_research_kit._runtime.cli import build_click_command as build_crkit_command
    from deployment.scripts.checks.core.surface import click_surface

    snapshot = json.loads((KIT_ROOT / "docs" / "guides" / "cli-surface.json").read_text(encoding="utf-8"))
    assert _jsonable(click_surface(build_click_command())) == snapshot["crk-ledger"]
    assert _jsonable(click_surface(build_crkit_command())) == snapshot["cr-kit"]


def _jsonable(surface: dict[str, object]) -> dict[str, object]:
    import json

    return json.loads(json.dumps(surface, default=str))
