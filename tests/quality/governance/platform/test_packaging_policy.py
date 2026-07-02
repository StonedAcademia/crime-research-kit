"""Governance: package metadata, extras, and release check wiring stay explicit."""

from __future__ import annotations

import json
import re
import subprocess
import sys

from tests.helpers import KIT_ROOT, moon_task_names

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


EXPECTED_EXTRAS = {
    "dev": {"pytest", "jsonschema", "beautifulsoup4", "trafilatura", "pandas", "networkx", "tomli"},
    "agentic": {"langgraph", "langgraph-checkpoint-sqlite"},
    "llm": {"langchain", "langchain-ollama"},
    "mcp": {"mcp"},
    "web-local": {"playwright", "scrapy", "trafilatura"},
    "documents": {"docling", "ocrmypdf", "pillow", "pymupdf"},
    "retrieval": {
        "diskcache",
        "llama-index-core",
        "llama-index-embeddings-huggingface",
        "llama-index-vector-stores-qdrant",
        "qdrant-client",
        "sentence-transformers",
    },
    "memory-local": {"mem0ai", "qdrant-client"},
    "governance": {"pip-audit", "pip-licenses", "cyclonedx-bom", "build", "tomli"},
}
EXPECTED_SCRIPTS = {
    "cr-kit": "cli:main",
    "crk-mcp": "adapters.interfaces.mcp.server:main",
}
REGISTRY_SHARDS = (
    "index.json",
    "env_vars.json",
    "lanes.schema.json",
    "lanes/public_records_core.json",
    "lanes/public_records_media.json",
    "lanes/review.json",
    "lanes/support.json",
    "templates/extraction.json",
)


def load_pyproject() -> dict:
    return tomllib.loads((KIT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def package_name(requirement: str) -> str:
    name = re.split(r"[<>=!~;\[]", requirement, maxsplit=1)[0].strip()
    return name.replace("_", "-").lower()


def test_core_package_has_no_runtime_dependencies_and_declares_license():
    project = load_pyproject()["project"]

    assert project["dependencies"] == []
    assert project["license"]["text"] == "AGPL-3.0-only"
    assert (KIT_ROOT / "LICENSE").exists()


def test_optional_dependency_groups_are_intentional():
    extras = load_pyproject()["project"]["optional-dependencies"]

    assert set(extras) == set(EXPECTED_EXTRAS)
    assert {extra: {package_name(req) for req in reqs} for extra, reqs in extras.items()} == EXPECTED_EXTRAS


def test_console_scripts_stay_stable():
    assert load_pyproject()["project"]["scripts"] == EXPECTED_SCRIPTS


def test_packaged_registry_data_matches_canonical_docs_registry():
    docs_registry = KIT_ROOT / "docs" / "registry"
    package_registry = KIT_ROOT / "src" / "core" / "lanes" / "registry_data"

    for rel in REGISTRY_SHARDS:
        assert json.loads((package_registry / rel).read_text(encoding="utf-8")) == json.loads(
            (docs_registry / rel).read_text(encoding="utf-8")
        )


def test_moon_uses_packaging_check_scripts():
    tooling = (KIT_ROOT / ".moon" / "tasks" / "tooling.yml").read_text(encoding="utf-8")

    assert {"audit-licenses", "build-dist"} <= moon_task_names()
    assert "deployment/scripts/checks/license_policy.py" in tooling
    assert "deployment/scripts/checks/fresh_build.py" in tooling
    assert "--exclude-mail" not in tooling


def test_packaging_smoke_imports_current_package_modules():
    fresh_build = (KIT_ROOT / "deployment" / "scripts" / "checks" / "fresh_build.py").read_text(encoding="utf-8")
    smoke = (KIT_ROOT / "deployment" / "scripts" / "checks" / "smoke" / "smoke-test.sh").read_text(encoding="utf-8")
    text = f"{fresh_build}\n{smoke}"

    assert "case_builder" not in text
    assert "import cli" in fresh_build
    assert "adapters.interfaces.mcp.server" in text


def test_license_policy_allows_agpl_project_and_copyleft_dependencies(tmp_path):
    records = [
        {"Name": "crime-research-kit", "Version": "0.11.1", "License": "AGPL-3.0-only"},
        {"Name": "chardet", "Version": "5.2.0", "License": "GNU Lesser General Public License v2 or later"},
        {"Name": "tld", "Version": "0.13.2", "License": "MPL-1.1 OR GPL-2.0-only OR LGPL-2.1-or-later"},
        {"Name": "setuptools", "Version": "79.0.1", "License": "UNKNOWN"},
    ]
    input_path = tmp_path / "licenses.json"
    input_path.write_text(json.dumps(records), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "deployment/scripts/checks/license_policy.py", "--input", str(input_path)],
        cwd=KIT_ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0
    assert "DENY" not in proc.stdout
    assert "REVIEW" not in proc.stdout


def test_license_policy_still_reviews_unmapped_unknowns(tmp_path):
    input_path = tmp_path / "licenses.json"
    input_path.write_text(
        json.dumps([{"Name": "example", "Version": "1.0.0", "License": "UNKNOWN"}]),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, "deployment/scripts/checks/license_policy.py", "--input", str(input_path)],
        cwd=KIT_ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0
    assert "REVIEW" in proc.stdout
    assert "example 1.0.0: UNKNOWN" in proc.stdout


def test_license_policy_still_denies_sspl_family(tmp_path):
    input_path = tmp_path / "licenses.json"
    input_path.write_text(
        json.dumps([{"Name": "example", "Version": "1.0.0", "License": "Server Side Public License"}]),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, "deployment/scripts/checks/license_policy.py", "--input", str(input_path)],
        cwd=KIT_ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 1
    assert "SSPL-family" in proc.stdout
