"""Governance for architecture docs describing the SDK boundary."""

from __future__ import annotations

from tests.helpers import KIT_ROOT


def read_doc(rel: str) -> str:
    return (KIT_ROOT / rel).read_text(encoding="utf-8")


def squashed(text: str) -> str:
    return " ".join(text.split())


def test_system_overview_shows_sdk_as_public_python_layer():
    text = read_doc("docs/guides/architecture/system-overview.md")
    flat = squashed(text)

    assert "## Public Python Boundary" in text
    assert "The public Python API is `crime_research_kit.sdk`." in text
    assert "`adapters`, `core`, and `pipeline` remain private runtime packages" in flat
    assert "`cr-kit` and `crk-mcp` are adapter surfaces over SDK/catalog-backed operations." in text
    assert "MCP-specific" in text
    assert "`run_report` remains a direct derived-report path" in text
    assert "MCP -->|SDK-backed tools| SDK" in text
    assert "run_report direct until public/private filtering" in text
    assert "MCP --> SDK" not in text
    assert "standard-library-only" not in text
    assert "standard library alone" not in text.lower()


def test_case_builder_doc_points_workflows_at_sdk_facade():
    text = read_doc("docs/guides/architecture/case-builder-langgraph.md")
    flat = squashed(text)

    assert "The public workflow API is `crime_research_kit.sdk.WorkflowClient`" in text
    assert "`CrkClient().workflows`" in text
    assert "CLI users reach the same boundary through `cr-kit plan`" in text
    assert "`pipeline.*` modules, graph nodes, and app service are private runtime internals" in flat
    assert "from crime_research_kit.sdk import CrkClient, CrkContext" in text
