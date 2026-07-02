from pathlib import Path

from case_builder.ops import extraction as extraction_ops
from case_builder.ops.runner import TrcrRunner
from tests.helpers import KIT_ROOT

REPO_ROOT = KIT_ROOT


def dry_runner() -> TrcrRunner:
    return TrcrRunner(repo_root=REPO_ROOT, dry_run=True)


def test_import_extraction_refuses_without_confirm():
    result = extraction_ops.import_extraction(dry_runner(), "data/cases/x", "staging/extractions/p.json")

    assert result.ok is False
    assert result.command == []
    assert any("confirm" in error for error in result.errors)


def test_import_extraction_plans_command_with_confirm():
    result = extraction_ops.import_extraction(
        dry_runner(),
        "data/cases/x",
        "staging/extractions/p.json",
        confirm=True,
    )

    assert result.ok is True
    assert result.command[2] == "import-extraction"


def test_draft_extraction_passes_template():
    result = extraction_ops.draft_extraction(dry_runner(), "data/cases/x", "S0001", template="missing-persons")

    assert result.command[2] == "draft-extraction"
    assert result.command[result.command.index("--template") + 1] == "missing-persons"


def test_save_and_read_and_list_packets(synthetic_case_copy):
    packet = {"source_id": "SDEMO0001", "entities": [{"name": "A Witness", "role": "witness"}]}

    saved = extraction_ops.save_packet(str(synthetic_case_copy), "SDEMO0001_extraction.json", packet)
    listed = extraction_ops.list_packets(str(synthetic_case_copy))
    read = extraction_ops.read_packet(str(synthetic_case_copy), "SDEMO0001_extraction.json")

    assert saved.ok is True
    assert "SDEMO0001_extraction.json" in listed.data["packets"]
    assert read.data["packet"] == packet
    actions = (synthetic_case_copy / "records" / "research_actions.jsonl").read_text(encoding="utf-8")
    assert "save_extraction_packet" in actions


def test_save_packet_rejects_guilt_label_without_citation(synthetic_case_copy):
    packet = {"entities": [{"name": "A Person", "role": "suspect"}]}

    result = extraction_ops.save_packet(str(synthetic_case_copy), "bad_packet.json", packet)

    assert result.ok is False
    assert not (synthetic_case_copy / "staging" / "extractions" / "bad_packet.json").exists()


def test_save_packet_rejects_path_escape(synthetic_case_copy):
    result = extraction_ops.save_packet(str(synthetic_case_copy), "../../records/claims.jsonl", {"a": 1})

    assert result.ok is False
    assert (synthetic_case_copy / "records" / "claims.jsonl").read_text(encoding="utf-8")


def test_read_packet_missing_is_failure(synthetic_case_copy):
    result = extraction_ops.read_packet(str(synthetic_case_copy), "nope.json")

    assert result.ok is False
