from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.helpers import KIT_ROOT


def make_stub_bin(tmp_path: Path) -> Path:
    stub = tmp_path / "bin"
    stub.mkdir()
    for name in ("proto", "uv"):
        path = stub / name
        path.write_text("#!/usr/bin/env sh\necho stub-" + name + " \"$@\"\n", encoding="utf-8")
        path.chmod(0o755)
    return stub


def test_bash_wrapper_toolchain_only_uses_existing_flow(tmp_path):
    env = {**os.environ, "PATH": f"{make_stub_bin(tmp_path)}:{os.environ['PATH']}"}
    result = subprocess.run(
        ["bash", "deployment/scripts/bootstrap.sh", "--toolchain-only"],
        cwd=KIT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "stub-proto use" in result.stdout
    assert "bootstrap_env.py" not in result.stdout


def test_bash_wrapper_configure_noninteractive_dry_run(tmp_path):
    env = {**os.environ, "PATH": f"{make_stub_bin(tmp_path)}:{os.environ['PATH']}"}
    result = subprocess.run(
        [
            "bash",
            "deployment/scripts/bootstrap.sh",
            "--configure",
            "--non-interactive",
            "--dry-run",
            "--workflow",
            "self-hosted",
            "--set",
            "CRK_SEARXNG_HOST_PORT=19082",
        ],
        cwd=KIT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Would write" in result.stdout
    assert "deployment/.env" in result.stdout


def test_bash_wrapper_non_tty_does_not_prompt(tmp_path):
    env = {**os.environ, "PATH": f"{make_stub_bin(tmp_path)}:{os.environ['PATH']}"}
    result = subprocess.run(
        ["bash", "deployment/scripts/bootstrap.sh"],
        cwd=KIT_ROOT,
        env=env,
        input="",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "To configure local deployment env later" in result.stdout


def test_powershell_wrapper_configure_noninteractive_dry_run(tmp_path):
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("pwsh is not available")
    env = {**os.environ, "PATH": f"{make_stub_bin(tmp_path)}:{os.environ['PATH']}"}
    result = subprocess.run(
        [
            pwsh,
            "deployment/scripts/bootstrap.ps1",
            "-Configure",
            "-NonInteractive",
            "-DryRun",
            "-Workflow",
            "self-hosted",
        ],
        cwd=KIT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Would write" in result.stdout
