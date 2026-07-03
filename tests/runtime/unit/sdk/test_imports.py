from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from tests.helpers import KIT_ROOT, ledger_command_args

LEGACY_ROOTS = {"adapters", "core", "pipeline"}


def drop_imported_roots(*roots: str) -> None:
    for name in list(sys.modules):
        if name in roots or any(name.startswith(f"{root}.") for root in roots):
            sys.modules.pop(name, None)


def test_sdk_imports_without_legacy_runtime_packages():
    drop_imported_roots("crime_research_kit", *LEGACY_ROOTS)

    sdk = importlib.import_module("crime_research_kit.sdk")

    assert sdk.CrkContext().case_dir is None
    assert sdk.CrkClient().case("demo").case_dir.as_posix() == "data/cases/demo"
    assert sdk.CrkClient().case("demo").extractions.case_dir.as_posix() == "data/cases/demo"
    assert sdk.CrkClient().case("demo").review.case_dir.as_posix() == "data/cases/demo"
    assert sdk.CrkClient().case("demo").exports.case_dir.as_posix() == "data/cases/demo"
    assert sdk.CrkClient().exports.context.dry_run is False
    assert sdk.CrkClient().workflows.context.dry_run is False
    assert sdk.CaseExtractionsClient
    assert sdk.CaseExportsClient
    assert sdk.ExportsClient
    assert sdk.CaseReviewClient
    assert sdk.WorkflowClient
    assert sdk.WorkflowPlanRequest
    assert sdk.WorkflowResumeRequest
    assert sdk.OperationResult(operation="case.info").ok is True
    assert sdk.OperationSpec.from_tags("example").tags == ()
    assert sdk.SafetyTier.READ.value == "read"
    assert sdk.get_operation("case.info").mcp_tool == "case_info"
    assert sdk.get_operation_for_http_route("post", "/v1/cases").name == "cases.create"
    assert sdk.http_route_bindings()[0].route.startswith("POST /v1/")
    assert len({binding.route for binding in sdk.HTTP_ROUTE_BINDINGS}) == len(sdk.HTTP_ROUTE_BINDINGS)
    assert sdk.list_operations()
    assert not (LEGACY_ROOTS & set(sys.modules))


def test_top_level_package_exports_only_sdk_namespace():
    drop_imported_roots("crime_research_kit", *LEGACY_ROOTS)

    package = importlib.import_module("crime_research_kit")

    assert package.__all__ == ["sdk"]
    assert package.sdk.CrkContext(dry_run=True).dry_run is True
    assert package.sdk.OperationResult(operation="case.info").operation == "case.info"
    assert not {"adapters", "core", "pipeline", "case_builder"} & set(package.__all__)
    assert not (LEGACY_ROOTS & set(sys.modules))


def test_sdk_examples_import_without_legacy_runtime_packages():
    drop_imported_roots("crime_research_kit", *LEGACY_ROOTS)

    examples = importlib.import_module("crime_research_kit.sdk.examples")

    assert examples.case_info_example
    assert examples.source_ingest_dry_run_example
    assert examples.packet_review_example
    assert examples.public_safe_export_example
    assert examples.workflow_resume_example
    assert not (LEGACY_ROOTS & set(sys.modules))


def test_sdk_examples_cover_minimal_recipes(synthetic_case_copy: Path, monkeypatch):
    from crime_research_kit.sdk.examples import (
        case_info_example,
        packet_review_example,
        public_safe_export_example,
        source_ingest_dry_run_example,
        workflow_resume_example,
    )
    from pipeline.app import service

    packet_path = synthetic_case_copy / "staging" / "extractions" / "SDEMO0001_extraction.json"
    packet = {"source_id": "SDEMO0001", "claims": [{"claim": "source-backed demo"}]}
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    def fake_resume(case_dir: str, **kwargs):
        return {
            "case_dir": case_dir,
            "thread_id": kwargs["thread_id"],
            "approved_packets": kwargs["approved_packets"],
            "export_approved": kwargs["export_approved"],
            "runner": "langgraph",
            "status": "bundle_exported",
        }

    monkeypatch.setattr(service, "resume_case_builder", fake_resume)

    info = case_info_example(cases_root=synthetic_case_copy.parent, repo_root=KIT_ROOT)
    ingest = source_ingest_dry_run_example(
        "https://example.org/source",
        cases_root=synthetic_case_copy.parent,
        case_slug="synthetic_case",
        repo_root=KIT_ROOT,
        title="Dry-run source",
        public_export=False,
    )
    packet_result = packet_review_example(
        "SDEMO0001_extraction.json",
        cases_root=synthetic_case_copy.parent,
        case_slug="synthetic_case",
        repo_root=KIT_ROOT,
    )
    export = public_safe_export_example(
        cases_root=synthetic_case_copy.parent,
        case_slug="synthetic_case",
        repo_root=KIT_ROOT,
    )
    resumed = workflow_resume_example(
        cases_root=synthetic_case_copy.parent,
        case_slug="synthetic_case",
        repo_root=KIT_ROOT,
        thread_id="sdk-example-thread",
        approved_packets=("SDEMO0001_extraction.json",),
        export_approved=True,
    )

    assert info.operation == "case.info"
    assert info.ok is True
    assert ingest.operation == "sources.ingest_url"
    assert ingest.diagnostics["dry_run"] is True
    assert "--no-public-export" in ledger_command_args(ingest.diagnostics["command"])
    assert packet_result.data["packet"] == packet
    assert export.operation == "exports.manim"
    assert export.data["privacy"]["include_private"] is False
    assert resumed.operation == "workflows.resume"
    assert resumed.data["thread_id"] == "sdk-example-thread"
