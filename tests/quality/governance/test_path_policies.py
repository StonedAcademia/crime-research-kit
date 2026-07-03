"""Governance: path naming, README coverage, and generic doc paths (spec §5)."""

from __future__ import annotations

import re
import subprocess

from tests.helpers import KIT_ROOT


# Policy source: docs/superpowers/specs/2026-07-02-governance-hardening-spec.md §5.
VAGUE_DIR_NAMES = {
    "misc",
    "old",
    "temp",
    "tmp",
    "stuff",
    "util",
    "utils",
    "helpers",
    "common",
    "shared",
    "new",
    "junk",
    "scratch",
}
APPROVED_VAGUE_DIRS: set[str] = set()
MACHINE_ROOT_RE = re.compile(r"(/home/[a-z_][a-z0-9_-]*/|/Users/|C:\\Users)")
README_REQUIRED_ROOTS = ("deployment/scripts", "docs/registry")
README_BUDGET_EXEMPT_DIRS = {
    # Existing governed dirs already at the 4-file shape limit.
    "deployment/scripts/tools",
    "deployment/scripts/tools/ufb/model",
    "docs/registry/lanes",
}


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=KIT_ROOT, check=True, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line]


def test_no_vague_directory_names():
    offenders: set[str] = set()
    for path in tracked_files():
        parts = path.split("/")[:-1]
        for depth, part in enumerate(parts, 1):
            rel = "/".join(parts[:depth])
            if part.lower() in VAGUE_DIR_NAMES and rel not in APPROVED_VAGUE_DIRS:
                offenders.add(rel)
    assert not offenders, f"vague directory names (spec §5): {sorted(offenders)}"


def test_docs_use_generic_paths_only():
    offenders = []
    for path in tracked_files():
        if not (path.startswith("docs/") or path == "README.md") or path.startswith("docs/superpowers/"):
            continue
        if not path.endswith((".md", ".json", ".yml", ".yaml", ".svg")):
            continue
        for lineno, line in enumerate((KIT_ROOT / path).read_text(errors="replace").splitlines(), 1):
            if MACHINE_ROOT_RE.search(line):
                offenders.append(f"{path}:{lineno}")
    assert not offenders, f"machine-specific paths in docs: {offenders}"


def test_workflow_dirs_have_readmes():
    dirs = {
        "/".join(path.split("/")[:-1])
        for path in tracked_files()
        if path.startswith(README_REQUIRED_ROOTS) and "/" in path
    }
    missing = sorted(
        directory
        for directory in dirs
        if directory not in README_BUDGET_EXEMPT_DIRS
        if not (KIT_ROOT / directory / "README.md").exists()
        and any(f"{directory}/" in path or path.startswith(f"{directory}/") for path in tracked_files())
    )
    assert not missing, f"dirs missing README.md ownership note: {missing}"
