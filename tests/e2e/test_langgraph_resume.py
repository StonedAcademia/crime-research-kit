import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("langgraph")

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from case_builder.graph.runner import build_case_builder_graph
from case_builder.models.state import CaseBuilderState
from case_builder.ops.runner import CrkRunner
from tests.helpers import KIT_ROOT

REPO_ROOT = KIT_ROOT


def make_graph(db_path: Path):
    """Build a fresh graph + saver on the same DB, simulating a process restart."""
    connection = sqlite3.connect(str(db_path), check_same_thread=False)
    runner = CrkRunner(repo_root=REPO_ROOT, dry_run=True)
    return build_case_builder_graph(runner, checkpointer=SqliteSaver(connection), use_interrupt=True)


def test_interrupt_resume_survives_graph_rebuild(tmp_path):
    db_path = tmp_path / "checkpoints.db"
    config = {"configurable": {"thread_id": "t-resume-1"}}
    state = CaseBuilderState(case_dir="data/cases/example_case", subject="missing person map")

    # Run 1: pauses at the packet review gate.
    graph = make_graph(db_path)
    graph.invoke(state.to_dict(), config)
    snapshot = graph.get_state(config)
    assert "packet_review_gate" in snapshot.next

    # "Restart": brand-new graph over the same sqlite file, then approve a packet.
    graph = make_graph(db_path)
    graph.invoke(Command(resume={"approved_packets": ["S0001_extraction.json"]}), config)
    snapshot = graph.get_state(config)
    assert "export_review_gate" in snapshot.next
    values = snapshot.values
    subcommands = [command[2] for command in values["planned_commands"]]
    assert "import-extraction" in subcommands
    assert "audit-contradictions" in subcommands

    # Final resume: approve the export; run completes.
    graph = make_graph(db_path)
    result = graph.invoke(Command(resume={"export_approved": True}), config)
    assert result["status"] == "bundle_exported"
    assert result["review_required"] is False
    subcommands = [command[2] for command in result["planned_commands"]]
    assert subcommands[-2:] == ["export-manim", "report"]


def test_rejecting_all_packets_ends_the_run(tmp_path):
    db_path = tmp_path / "checkpoints.db"
    config = {"configurable": {"thread_id": "t-reject-1"}}
    state = CaseBuilderState(case_dir="data/cases/example_case", subject="missing person map")

    graph = make_graph(db_path)
    graph.invoke(state.to_dict(), config)
    result = graph.invoke(
        Command(resume={"approved_packets": [], "rejected_packets": [{"packet": "S1.json", "reason": "bad extraction"}]}),
        config,
    )

    assert result["status"] == "packets_rejected"
    snapshot = graph.get_state(config)
    assert snapshot.next == ()  # routed to END, nothing pending
    subcommands = [command[2] for command in result["planned_commands"]]
    assert "import-extraction" not in subcommands
