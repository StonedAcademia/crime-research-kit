from crime_research_kit.sdk.operations import SafetyTier, get_operation, list_operations, operations_by_domain


def test_operation_catalog_has_unique_names_and_required_metadata():
    specs = list_operations()
    names = [spec.name for spec in specs]

    assert len(specs) >= 40
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
