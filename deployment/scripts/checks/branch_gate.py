#!/usr/bin/env python3
"""Run branch-specific moon gates for push hooks."""

from __future__ import annotations

import os
import subprocess
import sys
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ZERO_SHA = "0" * 40

BRANCH_TARGETS: dict[str, list[str]] = {
    "dev": ["crk:check", "crk:test-smoke"],
    "canary": ["crk:check", "crk:test-governance", "crk:test-smoke", "crk:audit-secrets"],
    "main": ["crk:check", "crk:test", "crk:audit-secrets"],
}
PREFIX_TARGETS: tuple[tuple[tuple[str, ...], list[str]], ...] = (
    (("docs/",), ["crk:check", "crk:test-governance"]),
    (("gov/", "test/", "chore/"), ["crk:check", "crk:test-governance", "crk:test-smoke"]),
    (("feat/", "fix/", "ci/"), ["crk:check", "crk:test-governance", "crk:test-smoke", "crk:test-integration"]),
)
UNKNOWN_TARGETS = ["crk:check", "crk:test"]


def run(command: list[str]) -> str:
    return subprocess.check_output(command, cwd=ROOT, text=True).strip()


def branch_from_ref(ref: str) -> str | None:
    if ref.startswith("refs/heads/"):
        return ref.removeprefix("refs/heads/")
    if ref in BRANCH_TARGETS:
        return ref
    return None


def current_branch() -> str | None:
    override = os.environ.get("CRK_HOOK_BRANCH")
    if override:
        return override
    try:
        return run(["git", "branch", "--show-current"])
    except subprocess.CalledProcessError:
        return None


def branches_from_pre_push(stdin: str) -> list[str]:
    branches: list[str] = []
    for line in stdin.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        local_ref, local_sha, remote_ref, _remote_sha = parts[:4]
        if local_sha == ZERO_SHA:
            continue
        branch = branch_from_ref(local_ref) or branch_from_ref(remote_ref)
        if branch and branch not in branches:
            branches.append(branch)
    return branches


def targets_for(branches: list[str]) -> list[str]:
    targets: list[str] = []
    for branch in branches:
        normalized = branch.lower()
        branch_targets = BRANCH_TARGETS.get(normalized)
        if branch_targets is None:
            branch_targets = next(
                (prefix_targets for prefixes, prefix_targets in PREFIX_TARGETS if normalized.startswith(prefixes)),
                UNKNOWN_TARGETS,
            )
        for target in branch_targets:
            if target not in targets:
                targets.append(target)
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print resolved targets without running moon.")
    args = parser.parse_args()

    stdin = sys.stdin.read()
    branches = branches_from_pre_push(stdin)
    if not branches:
        branch = current_branch()
        branches = [branch] if branch else []

    targets = targets_for(branches)
    if not targets:
        label = ", ".join(branches) if branches else "unknown branch"
        print(f"Skipping moon branch gate for {label}.")
        return 0

    print(f"Running moon branch gate for {', '.join(branches)}: {', '.join(targets)}", flush=True)
    if args.dry_run:
        return 0
    return subprocess.run(["moon", "run", *targets], cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
