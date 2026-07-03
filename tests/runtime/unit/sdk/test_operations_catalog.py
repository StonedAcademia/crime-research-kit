from __future__ import annotations

import json

from adapters.interfaces.mcp.tools.registry import DIRECT_TOOL_NAMES, sdk_tool_registrations, tool_registrations
from crime_research_kit.sdk.operations import SafetyTier, get_operation, list_operations, operations_by_domain
from tests.helpers import KIT_ROOT


DIRECT_MCP_TOOL_EXEMPTIONS = {"run_report"}
DIRECT_CLI_COMMAND_EXEMPTIONS = {"crk-ledger report"}


def test_operation_catalog_has_unique_names_and_required_metadata():
    specs = list_operations()
    names = [spec.name for spec in specs]

    assert len(specs) >= 39
    assert len(names) == len(set(names))
    assert names == sorted(names)
    assert all(spec.domain for spec in specs)
    assert all(spec.request_model.endswith("Request") for spec in specs)
    assert {spec.result_model for spec in specs} == {"OperationResult"}
    assert all(isinstance(spec.safety_tier, SafetyTier) for spec in specs)


def test_catalog_covers_initial_seed_operations():
    required = {
        "cases.create",
        "cases.list",
        "case.info",
        "records.list",
        "records.source_text",
        "sources.add",
        "sources.ingest_url",
        "extractions.draft",
        "extractions.import_reviewed",
        "review.audit_public_export",
        "exports.timeline",
        "workflows.plan",
        "workflows.resume",
    }

    assert required <= {spec.name for spec in list_operations()}


def test_catalog_records_safety_and_adapter_mappings():
    import_reviewed = get_operation("extractions.import_reviewed")
    audit_public = get_operation("review.audit_public_export")
    timeline = get_operation("exports.timeline")

    assert import_reviewed.safety_tier is SafetyTier.CANONICAL_GATED
    assert import_reviewed.cli_command == "crk-ledger import-extraction"
    assert import_reviewed.mcp_tool == "import_extraction"
    assert import_reviewed.skill_api_name == "importExtraction"
    assert import_reviewed.http_route == "POST /v1/cases/{case_slug}/extractions:import"
    assert "canonical JSONL records" in import_reviewed.side_effects

    assert audit_public.safety_tier is SafetyTier.PUBLIC_EXPORT
    assert audit_public.http_route == "POST /v1/cases/{case_slug}:audit-public-export"
    assert timeline.requires_case is False


def test_catalog_preserves_alias_and_optional_capability_metadata():
    source_independence = get_operation("review.audit_source_independence")
    discovery = get_operation("sources.discover")
    retrieval = get_operation("retrieval.query")
    memory = get_operation("memory.remember_research_actions")

    assert source_independence.cli_aliases == ("source-independence",)
    assert discovery.optional_extra == "web-local"
    assert "optional" in discovery.tags
    assert retrieval.optional_extra == "retrieval"
    assert memory.optional_extra == "memory-local"


def test_catalog_can_be_grouped_by_domain():
    exports = operations_by_domain("exports")

    assert {spec.name for spec in exports} == {
        "exports.analysis_charts",
        "exports.case_charts",
        "exports.manim",
        "exports.people_clusters",
        "exports.timeline",
    }


def test_cli_commands_have_catalog_entries_or_explicit_exemptions():
    surface = json.loads((KIT_ROOT / "docs/guides/cli-surface.json").read_text(encoding="utf-8"))
    specs_by_cli = {spec.cli_command: spec for spec in list_operations() if spec.cli_command}
    command_names = {
        f"{script} {command}"
        for script, commands in surface.items()
        for command in commands
    }

    assert command_names - set(specs_by_cli) - DIRECT_CLI_COMMAND_EXEMPTIONS == set()
    assert DIRECT_CLI_COMMAND_EXEMPTIONS <= command_names
    assert DIRECT_CLI_COMMAND_EXEMPTIONS.isdisjoint(specs_by_cli)
    for script, commands in surface.items():
        for command, metadata in commands.items():
            if f"{script} {command}" in DIRECT_CLI_COMMAND_EXEMPTIONS:
                continue
            aliases = set(metadata.get("aliases") or [])
            if aliases:
                spec = specs_by_cli[f"{script} {command}"]
                assert aliases <= set(spec.cli_aliases)


def test_mcp_tools_have_catalog_entries_or_explicit_exemptions():
    tool_names = {entry.tool_name for entry in tool_registrations()}
    sdk_tool_names = {entry.tool_name for entry in sdk_tool_registrations()}
    catalog_tools = {spec.mcp_tool for spec in list_operations() if spec.mcp_tool}

    assert sdk_tool_names == catalog_tools
    assert tool_names - catalog_tools - DIRECT_MCP_TOOL_EXEMPTIONS == set()
    assert DIRECT_TOOL_NAMES == DIRECT_MCP_TOOL_EXEMPTIONS
    assert DIRECT_MCP_TOOL_EXEMPTIONS.isdisjoint(catalog_tools)


def test_mcp_registry_carries_catalog_metadata_and_handler_refs():
    expected = {spec.mcp_tool: spec for spec in list_operations() if spec.mcp_tool}
    registered = {entry.tool_name: entry for entry in sdk_tool_registrations()}

    assert set(registered) == set(expected)
    for tool_name, spec in expected.items():
        entry = registered[tool_name]
        assert entry.operation_name == spec.name
        assert entry.operation == spec
        assert entry.operation.safety_tier is spec.safety_tier
        assert entry.summary
        assert callable(entry.handler())


def test_mcp_registry_keeps_direct_tools_prompts_and_resources_explicit():
    registrations = {entry.tool_name: entry for entry in tool_registrations()}
    direct = {name: entry for name, entry in registrations.items() if not entry.sdk_backed}

    assert set(direct) == DIRECT_MCP_TOOL_EXEMPTIONS
    assert direct["run_report"].operation is None
    assert direct["run_report"].direct_reason
    assert {"start_case", "process_source", "review_packet", "public_readiness"}.isdisjoint(registrations)
    assert {"case_json", "records", "packet", "reference"}.isdisjoint(registrations)


def test_direct_mcp_tool_exemptions_are_documented():
    overview = (KIT_ROOT / "docs/guides/architecture/system-overview.md").read_text(encoding="utf-8")
    mcp_guide = (KIT_ROOT / "docs/guides/integrations/mcp-server.md").read_text(encoding="utf-8")
    operation_docs = (KIT_ROOT / "docs/guides/integrations/skill-api/operations/README.md").read_text(encoding="utf-8")
    flat_operation_docs = " ".join(operation_docs.split())

    assert "`run_report` remains a direct derived-report path" in overview
    assert "`run_report` remains a direct MCP/runtime exception" in mcp_guide
    assert "`crk-ledger report`, `reportCase`, and MCP `run_report`" in flat_operation_docs
