"""Governance: pinned tooling manifest stays consistent with pyproject and make targets."""

import json
import re

from tests.helpers import KIT_ROOT


MANIFEST = KIT_ROOT / "deployment" / "tooling" / "manifest.json"
REQUIRED_TOOLS = {"gitleaks", "lychee"}
REQUIRED_PYTHON_PINS = {"pip-audit", "pip-licenses", "cyclonedx-bom"}
AUDIT_TARGETS = {"audit-secrets", "audit-deps", "audit-licenses", "audit-links", "sbom", "build-dist"}


def test_manifest_pins_tools_with_checksums():
    data = json.loads(MANIFEST.read_text())
    assert REQUIRED_TOOLS <= set(data["tools"])
    for name, tool in data["tools"].items():
        assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", tool["version"]), name
        assert tool["sha256"], f"{name} missing checksums"


def test_python_pins_match_governance_extra():
    data = json.loads(MANIFEST.read_text())
    pyproject = (KIT_ROOT / "pyproject.toml").read_text()
    for pkg, version in data["python_pins"].items():
        assert f"{pkg}=={version}" in pyproject, f"{pkg} pin drift"
    assert REQUIRED_PYTHON_PINS <= set(data["python_pins"])


def test_make_exposes_audit_lane_targets():
    makefile = (KIT_ROOT / "Makefile").read_text()
    for target in AUDIT_TARGETS:
        assert f"\n{target}:" in makefile, f"make target {target} missing"
