from pathlib import Path

from pipeline.graph.nodes.pipeline import (
    draft_packets_node,
    merge_results,
    source_capture_node,
)
from adapters.ops.result import OpResult
from adapters.ops.runner import CrkRunner
from tests.helpers import KIT_ROOT

REPO_ROOT = KIT_ROOT


def dry_runner() -> CrkRunner:
    return CrkRunner(repo_root=REPO_ROOT, dry_run=True)


def test_merge_results_folds_commands_and_errors():
    state = {"planned_commands": [["old"]], "tool_results": [], "errors": ["old error"]}
    results = [
        OpResult(name="a", command=["cmd", "a"]),
        OpResult(name="b", ok=False, command=["cmd", "b"], errors=["b failed"]),
    ]

    update = merge_results(state, results, "done")

    assert update["planned_commands"] == [["old"], ["cmd", "a"], ["cmd", "b"]]
    assert [item["name"] for item in update["tool_results"]] == ["a", "b"]
    assert update["errors"] == ["old error", "b failed"]
    assert update["status"] == "error"


def test_merge_results_success_status_when_all_ok():
    update = merge_results({}, [OpResult(name="a", command=["x"])], "done")

    assert update["status"] == "done"


def test_source_capture_skips_without_urls():
    node = source_capture_node(dry_runner())

    update = node({"case_dir": "data/cases/x"})

    assert update["status"] == "source_capture_skipped"


def test_source_capture_plans_ingest_per_url():
    node = source_capture_node(dry_runner())

    update = node({"case_dir": "data/cases/x", "source_urls": ["https://a.example", "https://b.example"]})

    assert update["status"] == "sources_captured"
    assert [item["name"] for item in update["tool_results"]] == ["ingest_url", "ingest_url"]
    assert update["planned_commands"][0][2] == "ingest-url"


def test_draft_packets_skips_in_dry_run_without_source_ids():
    node = draft_packets_node(dry_runner())

    update = node({"case_dir": "data/cases/x"})

    assert update["status"] == "draft_skipped_no_sources"


def test_draft_packets_plans_draft_per_source_id():
    node = draft_packets_node(dry_runner())

    update = node({"case_dir": "data/cases/x", "source_ids": ["S0001", "S0002"]})

    assert update["status"] == "packets_drafted"
    assert len(update["planned_commands"]) == 2
    assert update["planned_commands"][0][2] == "draft-extraction"


def test_parse_or_ocr_skips_in_dry_run():
    from pipeline.graph.nodes.pipeline import parse_or_ocr_node

    node = parse_or_ocr_node(dry_runner())

    update = node({"case_dir": "data/cases/x"})

    assert update["status"] == "parse_skipped_dry_run"


def test_parse_or_ocr_records_runtime_errors_per_source(synthetic_case_copy):
    from pipeline.graph.nodes.pipeline import parse_or_ocr_node

    node = parse_or_ocr_node(CrkRunner(repo_root=REPO_ROOT, dry_run=False))

    update = node({"case_dir": str(synthetic_case_copy)})

    # Synthetic case sources either already have text or lack local raw files /
    # Docling; the node must finish without raising and report per-source issues.
    assert update["status"] in {"sources_parsed", "error"}
    assert isinstance(update.get("errors", []), list)


def test_import_and_validate_skips_without_approvals():
    from pipeline.graph.nodes.pipeline import import_and_validate_node

    node = import_and_validate_node(dry_runner())

    update = node({"case_dir": "data/cases/x"})

    assert update["status"] == "import_skipped_no_approved_packets"


def test_import_and_validate_imports_each_approved_packet_with_confirm():
    from pipeline.graph.nodes.pipeline import import_and_validate_node

    node = import_and_validate_node(dry_runner())

    update = node({"case_dir": "data/cases/x", "approved_packets": ["S1_extraction.json", "S2_extraction.json"]})

    assert update["status"] == "imported_and_validated"
    names = [item["name"] for item in update["tool_results"]]
    assert names == ["import_extraction", "import_extraction", "validate"]
    assert update["planned_commands"][0][2] == "import-extraction"
    assert update["planned_commands"][0][4].endswith("staging/extractions/S1_extraction.json")
    assert not update["errors"]  # confirm=True flowed through the gate


def test_index_node_skips_unless_enabled():
    from pipeline.graph.nodes.pipeline import index_case_node

    node = index_case_node(dry_runner())

    assert node({"case_dir": "data/cases/x"})["status"] == "index_skipped"
    assert node({"case_dir": "data/cases/x", "index_enabled": True})["status"] == "index_skipped"  # dry run


def test_index_node_reports_failure_without_raising(synthetic_case_copy):
    from pipeline.graph.nodes.pipeline import index_case_node
    from adapters.ops.runner import CrkRunner

    node = index_case_node(CrkRunner(repo_root=REPO_ROOT, dry_run=False))

    update = node({"case_dir": str(synthetic_case_copy), "index_enabled": True})

    # Retrieval extras / Qdrant are not available in CI: the node must degrade.
    assert update["status"] in {"case_indexed", "index_failed"}


def test_readiness_audit_runs_four_audits():
    from pipeline.graph.nodes.pipeline import readiness_audit_node

    node = readiness_audit_node(dry_runner())

    update = node({"case_dir": "data/cases/x"})

    subcommands = [command[2] for command in update["planned_commands"]]
    assert subcommands == [
        "audit-contradictions",
        "review-narrative-readiness",
        "audit-privacy-redactions",
        "audit-source-independence",
    ]
    assert update["status"] == "readiness_audited"


def test_export_bundle_exports_manim_and_report():
    from pipeline.graph.nodes.pipeline import export_bundle_node

    node = export_bundle_node(dry_runner())

    update = node({"case_dir": "data/cases/x"})

    subcommands = [command[2] for command in update["planned_commands"]]
    assert subcommands == ["export-manim", "report"]
    assert update["status"] == "bundle_exported"
    assert update["review_required"] is False
    assert "--include-private" not in update["planned_commands"][0]
