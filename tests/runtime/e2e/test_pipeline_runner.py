from pathlib import Path

from pipeline.graph.runner import run_sequential
from core.models.state import CaseBuilderState
from adapters.ops.runner import CrkRunner
from tests.helpers import KIT_ROOT

REPO_ROOT = KIT_ROOT


def dry_runner() -> CrkRunner:
    return CrkRunner(repo_root=REPO_ROOT, dry_run=True)


def test_sequential_dry_run_stops_at_packet_gate():
    result = run_sequential(
        CaseBuilderState(case_dir="data/cases/example_case", title="Example", subject="missing person map"),
        dry_runner(),
    )

    assert result["status"] == "waiting_for_human_review"
    assert result["review_required"] is True
    # Nothing after the packet gate ran:
    subcommands = [command[2] for command in result["planned_commands"]]
    assert "import-extraction" not in subcommands
    assert "export-manim" not in subcommands


def test_sequential_full_pass_with_preapprovals_runs_whole_pipeline():
    result = run_sequential(
        CaseBuilderState(
            case_dir="data/cases/example_case",
            title="Example",
            subject="missing person map",
            source_urls=["https://example.com/story"],
            source_ids=["S0001"],
            approved_packets=["S0001_extraction.json"],
            export_approved=True,
        ),
        dry_runner(),
    )

    assert result["status"] == "bundle_exported"
    assert result["review_required"] is False
    subcommands = [command[2] for command in result["planned_commands"]]
    assert subcommands == [
        "init-case",
        "plan-public-records",
        "ingest-url",
        "draft-extraction",
        "import-extraction",
        "validate",
        "audit-contradictions",
        "review-narrative-readiness",
        "audit-privacy-redactions",
        "audit-source-independence",
        "export-manim",
        "report",
    ]


def test_checkpointer_creates_runs_db(tmp_path):
    import pytest

    pytest.importorskip("langgraph")
    from pipeline.graph.persistence.checkpoint import case_checkpointer

    saver = case_checkpointer(str(tmp_path / "some_case"))

    assert (tmp_path / "some_case" / ".runs" / "checkpoints.db").exists()
    assert saver is not None
