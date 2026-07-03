"""Governance: public commands stay covered by operator runbooks."""

from __future__ import annotations

from adapters.interfaces.cli.app import build_click_command
from cli import build_click_command as build_crkit_command
from tests.helpers import KIT_ROOT, moon_task_names


RUNBOOK_ROOT = KIT_ROOT / "docs" / "guides" / "runbooks"

RUNBOOK_EXEMPT = {
    # Compatibility alias for audit-source-independence; the canonical command is documented.
    "crk-ledger source-independence",
}


def cr_kit_commands() -> set[str]:
    return {f"cr-kit {name}" for name in build_crkit_command().commands}


def ledger_commands() -> set[str]:
    return {f"crk-ledger {name}" for name in build_click_command().commands}


def docker_moon_targets() -> set[str]:
    return {f"moon run crk:{name}" for name in moon_task_names() if name.startswith("docker-")}


def runbook_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in RUNBOOK_ROOT.rglob("*.md"))


def test_public_commands_are_covered_by_runbooks():
    commands = cr_kit_commands() | ledger_commands() | docker_moon_targets()
    docs = runbook_text()
    missing = sorted(command for command in commands if command not in RUNBOOK_EXEMPT and command not in docs)
    assert not missing, "public commands missing from runbooks:\n" + "\n".join(missing)
