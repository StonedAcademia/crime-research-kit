"""Governance: GitHub workflows stay thin make callers and match branch gates."""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

from tests.helpers import KIT_ROOT


WORKFLOWS = KIT_ROOT / ".github" / "workflows"


def make_targets() -> set[str]:
    text = (KIT_ROOT / "Makefile").read_text(encoding="utf-8")
    return {match.group(1) for match in re.finditer(r"^([A-Za-z0-9_-]+):", text, re.MULTILINE)}


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


def test_workflow_run_steps_are_make_targets():
    targets = make_targets()
    failures: list[str] = []
    for workflow, lineno, command in workflow_run_commands():
        parts = command.split()
        if not parts or parts[0] != "make":
            failures.append(f"{workflow}:{lineno} does not start with make: {command}")
            continue
        for target in parts[1:]:
            if target not in targets:
                failures.append(f"{workflow}:{lineno} unknown make target: {target}")
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
