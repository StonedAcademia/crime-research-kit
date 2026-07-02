"""Governance: package metadata, extras, and release check wiring stay explicit."""

from __future__ import annotations

import re
import tomllib
import json

from tests.helpers import KIT_ROOT, moon_task_names


EXPECTED_EXTRAS = {
    "dev": {"pytest", "jsonschema", "beautifulsoup4", "trafilatura", "pandas", "networkx"},
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
    "governance": {"pip-audit", "pip-licenses", "cyclonedx-bom", "build"},
}
EXPECTED_SCRIPTS = {
    "cr-kit": "cli:main",
    "crk-ledger": "adapters.interfaces.cli.entry:main",
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
    assert project["license"]["text"] == "MIT"
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
