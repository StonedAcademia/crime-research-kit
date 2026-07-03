"""Governance for the public Python SDK import boundary."""

from __future__ import annotations

import re
from pathlib import Path

from tests.helpers import KIT_ROOT

PUBLIC_DOC_ROOTS = (
    KIT_ROOT / "README.md",
    KIT_ROOT / "CHANGELOG.md",
    KIT_ROOT / "docs" / "README.md",
    KIT_ROOT / "docs" / "guides",
    KIT_ROOT / "src" / "crime_research_kit" / "README.md",
    KIT_ROOT / "src" / "crime_research_kit" / "sdk" / "README.md",
)
PRIVATE_IMPORT_RE = re.compile(r"(?:^|[`>])\s*(?:from|import)\s+(adapters|core|pipeline|case_builder)(?:\b|\.)")


def iter_public_markdown() -> list[Path]:
    paths: list[Path] = []
    for root in PUBLIC_DOC_ROOTS:
        if root.is_file():
            paths.append(root)
        else:
            paths.extend(sorted(root.rglob("*.md")))
    return sorted(set(paths))


def test_python_sdk_boundary_policy_is_documented():
    policy = KIT_ROOT / "docs" / "guides" / "integrations" / "python-sdk.md"
    text = policy.read_text(encoding="utf-8")

    assert "The public Python SDK import root is `crime_research_kit.sdk`." in text
    assert "adapters.*" in text
    assert "core.*" in text
    assert "pipeline.*" in text
    assert "private runtime" in text


def test_public_docs_do_not_advertise_runtime_imports():
    offenders = []
    for path in iter_public_markdown():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if PRIVATE_IMPORT_RE.search(line):
                offenders.append(f"{path.relative_to(KIT_ROOT)}:{lineno}: {line.strip()}")

    assert not offenders, offenders
