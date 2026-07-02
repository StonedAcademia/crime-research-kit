"""Governance: release readiness changelog and tag/version checks."""

from __future__ import annotations

import importlib.util
import textwrap

import pytest

from tests.helpers import KIT_ROOT


def load_release_readiness():
    path = KIT_ROOT / "deployment" / "scripts" / "checks" / "release" / "release_readiness.py"
    spec = importlib.util.spec_from_file_location("release_readiness", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_changelog_has_unreleased_and_current_version():
    rr = load_release_readiness()
    text = (KIT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    sections = rr.changelog_sections(text)
    assert "Unreleased" in sections
    rr.check_changelog(text, "0.10.0")


def test_tag_must_match_pyproject_version():
    rr = load_release_readiness()

    rr.check_tag_matches_version("v0.10.0", "0.10.0")
    with pytest.raises(rr.ReleaseError):
        rr.check_tag_matches_version("v0.11.0", "0.10.0")


def test_version_and_tag_must_be_semver():
    rr = load_release_readiness()

    with pytest.raises(rr.ReleaseError):
        rr.check_tag_matches_version("v0.10", "0.10.0")
    with pytest.raises(rr.ReleaseError):
        rr.check_tag_matches_version("v0.10.0", "0.10")


def test_changelog_requires_dated_release_section():
    rr = load_release_readiness()
    text = textwrap.dedent(
        """\
        # Changelog

        ## [Unreleased]

        ## [0.10.0]
        """
    )

    with pytest.raises(rr.ReleaseError):
        rr.check_changelog(text, "0.10.0")


def test_changelog_requires_substantial_release_coverage():
    rr = load_release_readiness()
    text = textwrap.dedent(
        """\
        # Changelog

        ## [Unreleased]

        ## [0.10.0] - 2026-07-02

        ### Added

        - One placeholder entry.
        """
    )

    with pytest.raises(rr.ReleaseError):
        rr.check_changelog(text, "0.10.0")
