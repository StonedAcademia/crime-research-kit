"""Governance: public commands stay covered by operator runbooks."""

from __future__ import annotations

import os
import re
import subprocess
import sys

from tests.helpers import KIT_ROOT


RUNBOOK_ROOT = KIT_ROOT / "docs" / "guides" / "runbooks"
TCR = KIT_ROOT / ".agents" / "skills" / "truecrime-cult-research" / "scripts" / "tcr.py"

RUNBOOK_EXEMPT = {
    # Compatibility alias for audit-source-independence; the canonical command is documented.
    "tcr.py source-independence",
}


def run_help(args: list[str]) -> str:
    env = {**os.environ, "PYTHONPATH": str(KIT_ROOT / "src")}
    return subprocess.run(args, cwd=KIT_ROOT, check=True, capture_output=True, text=True, env=env).stdout


def subcommands_from_help(output: str) -> list[str]:
    match = re.search(r"\{([^}]+)\}", output)
    assert match, output
    return [item.strip() for item in match.group(1).split(",") if item.strip()]


def cr_kit_commands() -> set[str]:
    output = run_help([sys.executable, "-m", "cli", "--help"])
    return {f"cr-kit {name}" for name in subcommands_from_help(output)}


def tcr_commands() -> set[str]:
    output = run_help([sys.executable, str(TCR), "--help"])
    return {f"tcr.py {name}" for name in subcommands_from_help(output)}


def docker_make_targets() -> set[str]:
    makefile = (KIT_ROOT / "Makefile").read_text(encoding="utf-8")
    return {f"make {match.group(1)}" for match in re.finditer(r"^(docker-[A-Za-z0-9_-]+):", makefile, re.MULTILINE)}


def runbook_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in RUNBOOK_ROOT.rglob("*.md"))


def test_public_commands_are_covered_by_runbooks():
    commands = cr_kit_commands() | tcr_commands() | docker_make_targets()
    docs = runbook_text()
    missing = sorted(command for command in commands if command not in RUNBOOK_EXEMPT and command not in docs)
    assert not missing, "public commands missing from runbooks:\n" + "\n".join(missing)
