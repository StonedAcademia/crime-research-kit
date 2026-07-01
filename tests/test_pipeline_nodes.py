from pathlib import Path

from case_builder.graph.pipeline_nodes import (
    draft_packets_node,
    merge_results,
    source_capture_node,
)
from case_builder.ops.result import OpResult
from case_builder.ops.runner import TrcrRunner

REPO_ROOT = Path(__file__).resolve().parents[1]


def dry_runner() -> TrcrRunner:
    return TrcrRunner(repo_root=REPO_ROOT, dry_run=True)


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
    from case_builder.graph.pipeline_nodes import parse_or_ocr_node

    node = parse_or_ocr_node(dry_runner())

    update = node({"case_dir": "data/cases/x"})

    assert update["status"] == "parse_skipped_dry_run"


def test_parse_or_ocr_records_runtime_errors_per_source(synthetic_case_copy):
    from case_builder.graph.pipeline_nodes import parse_or_ocr_node

    node = parse_or_ocr_node(TrcrRunner(repo_root=REPO_ROOT, dry_run=False))

    update = node({"case_dir": str(synthetic_case_copy)})

    # Synthetic case sources either already have text or lack local raw files /
    # Docling; the node must finish without raising and report per-source issues.
    assert update["status"] in {"sources_parsed", "error"}
    assert isinstance(update.get("errors", []), list)
