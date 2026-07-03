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


EXPECTED_REQUIRED_DEPENDENCIES = {
    "jsonschema",
    "pydantic",
    "pydantic-settings",
    "httpx",
    "typer",
    "jinja2",
}
EXPECTED_EXTRAS = {
    "dev": {"pytest", "beautifulsoup4", "trafilatura", "pandas", "networkx", "tomli"},
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
    "crk-ledger": "adapters.interfaces.cli.entry:main",
    "crk-mcp": "adapters.interfaces.mcp.server:main",
}
TEMPORARY_RUNTIME_PACKAGE_INCLUDES = {"adapters*", "core*", "pipeline*"}
RUNTIME_NAMESPACE = "crime_research_kit._runtime."
TOP_LEVEL_RUNTIME_PREFIXES = ("adapters.", "core.", "pipeline.")
REGISTRY_SHARDS = (
    "index.json",
    "env_vars.json",
    "lanes.schema.json",
    "lanes/public_records_core.json",
    "lanes/public_records_media.json",
    "lanes/review.json",
    "lanes/support.json",
    "templates/extraction.json",
    "analysis/vocabulary.json",
    "analysis/scoring.json",
)
SCHEMA_SHARDS = (
    "case/artifact.schema.json",
    "case/entity.schema.json",
    "case/place.schema.json",
    "case/source.schema.json",
    "evidence/claim.schema.json",
    "evidence/event.schema.json",
    "evidence/event_link.schema.json",
    "evidence/relationship.schema.json",
    "review/quote.schema.json",
    "review/redaction.schema.json",
    "review/research_action.schema.json",
    "review/source_span.schema.json",
)


def load_pyproject() -> dict:
    return tomllib.loads((KIT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def package_name(requirement: str) -> str:
    name = re.split(r"[<>=!~;\[]", requirement, maxsplit=1)[0].strip()
    return name.replace("_", "-").lower()


def test_required_dependencies_stay_pinned_to_the_allowlist():
    project = load_pyproject()["project"]

    assert {package_name(req) for req in project["dependencies"]} == EXPECTED_REQUIRED_DEPENDENCIES
    assert project["license"]["text"] == "AGPL-3.0-only"
    assert (KIT_ROOT / "LICENSE").exists()


def test_optional_dependency_groups_are_intentional():
    extras = load_pyproject()["project"]["optional-dependencies"]

    assert set(extras) == set(EXPECTED_EXTRAS)
    assert {extra: {package_name(req) for req in reqs} for extra, reqs in extras.items()} == EXPECTED_EXTRAS


def test_console_scripts_stay_stable():
    assert load_pyproject()["project"]["scripts"] == EXPECTED_SCRIPTS


def test_public_sdk_namespace_is_packaged():
    package_include = load_pyproject()["tool"]["setuptools"]["packages"]["find"]["include"]

    assert "crime_research_kit*" in package_include


def test_runtime_package_discovery_waits_for_runtime_metadata_move():
    pyproject = load_pyproject()
    package_include = set(pyproject["tool"]["setuptools"]["packages"]["find"]["include"])
    missing_includes = sorted(TEMPORARY_RUNTIME_PACKAGE_INCLUDES - package_include)
    if not missing_includes:
        return

    scripts = pyproject["project"]["scripts"]
    package_data = pyproject["tool"]["setuptools"].get("package-data", {})
    unmigrated_scripts = {name: target for name, target in scripts.items() if not target.startswith(RUNTIME_NAMESPACE)}
    unmigrated_data = sorted(key for key in package_data if key.startswith(TOP_LEVEL_RUNTIME_PREFIXES))
    runtime_data = sorted(key for key in package_data if key.startswith(RUNTIME_NAMESPACE))

    assert not unmigrated_scripts and runtime_data and not unmigrated_data, (
        "Do not remove top-level runtime packages from package discovery before "
        "console scripts and package-data keys move under crime_research_kit._runtime. "
        f"missing includes={missing_includes}; "
        f"unmigrated scripts={unmigrated_scripts}; "
        f"unmigrated package-data keys={unmigrated_data}; "
        f"runtime package-data keys={runtime_data}"
    )


def test_packaged_registry_data_matches_canonical_docs_registry():
    docs_registry = KIT_ROOT / "docs" / "registry"
    package_registry = KIT_ROOT / "src" / "core" / "lanes" / "registry_data"

    for rel in REGISTRY_SHARDS:
        assert json.loads((package_registry / rel).read_text(encoding="utf-8")) == json.loads(
            (docs_registry / rel).read_text(encoding="utf-8")
        )


def test_packaged_schema_data_matches_canonical_docs_schemas():
    docs_schemas = KIT_ROOT / "docs" / "schemas"
    package_schemas = KIT_ROOT / "src" / "core" / "models" / "schemas_data"

    for rel in SCHEMA_SHARDS:
        assert json.loads((package_schemas / rel).read_text(encoding="utf-8")) == json.loads(
            (docs_schemas / rel).read_text(encoding="utf-8")
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
    assert "import crime_research_kit.sdk" in fresh_build
    assert "import crime_research_kit.sdk.examples" in fresh_build
    assert "adapters.interfaces.mcp.server" in text


def test_report_frontend_assets_are_committed_and_selfcontained():
    static = KIT_ROOT / "src/adapters/ops/evidence/reports/analysis/pages/templates_data/static"
    css_path, js_path = static / "app.css", static / "app.js"

    assert css_path.exists() and js_path.exists()
    css, js = css_path.read_text(encoding="utf-8"), js_path.read_text(encoding="utf-8")
    assert len(css) > 500 and len(js) > 500
    assert "https://tailwindcss.com" in css
    for text in (css.replace("https://tailwindcss.com", ""), js):
        assert "http://" not in text
        assert "https://" not in text
        assert "fetch(" not in text
        assert re.search(r"""(?:src|href)=["']https?://""", text) is None


def test_license_policy_allows_agpl_project_and_copyleft_dependencies(tmp_path):
    records = [
        {"Name": "crime-research-kit", "Version": "0.13.0", "License": "AGPL-3.0-only"},
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
