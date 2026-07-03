from __future__ import annotations

import json
from pathlib import Path

from crime_research_kit.sdk import CrkClient, CrkContext
from crime_research_kit.sdk.errors import INVALID_INPUT, SAFETY_BLOCKED
from tests.helpers import KIT_ROOT, ledger_command_args, ledger_subcommand


def client_for(case_dir: Path, *, dry_run: bool = False) -> CrkClient:
    return CrkClient(CrkContext(repo_root=KIT_ROOT, cases_root=case_dir.parent, dry_run=dry_run))


def test_extractions_draft_plans_template_and_excerpt(synthetic_case_copy: Path):
    result = client_for(synthetic_case_copy, dry_run=True).case("synthetic_case").extractions.draft(
        "SDEMO0001",
        template="missing-persons",
        excerpt_chars=1200,
    )

    args = ledger_command_args(result.diagnostics["command"])
    assert result.ok is True
    assert result.operation == "extractions.draft"
    assert args[:3] == ["draft-extraction", str(synthetic_case_copy), "SDEMO0001"]
    assert args[args.index("--template") + 1] == "missing-persons"
    assert args[args.index("--excerpt-chars") + 1] == "1200"


def test_extractions_save_read_and_list_packet(synthetic_case_copy: Path):
    case = client_for(synthetic_case_copy).case("synthetic_case")
    packet = {"source_id": "SDEMO0001", "entities": [{"name": "A Witness", "role": "witness"}]}

    saved = case.extractions.save("SDEMO0001_extraction.json", packet)
    listed = case.extractions.list()
    read = case.extractions.read("SDEMO0001_extraction.json")

    packet_path = synthetic_case_copy / "staging" / "extractions" / "SDEMO0001_extraction.json"
    assert saved.ok is True
    assert saved.operation == "extractions.save"
    assert saved.outputs == [str(packet_path)]
    assert listed.data["packets"] == ["SDEMO0001_extraction.json"]
    assert listed.counts == {"packets": 1}
    assert read.data["packet"] == packet
    assert read.outputs == [str(packet_path)]


def test_extractions_save_rejects_guilt_labels(synthetic_case_copy: Path):
    packet = {"entities": [{"name": "A Person", "role": "suspect"}]}

    result = client_for(synthetic_case_copy).case("synthetic_case").extractions.save("bad.json", packet)

    assert result.ok is False
    assert result.operation == "extractions.save"
    assert result.errors[0].code == SAFETY_BLOCKED
    assert not (synthetic_case_copy / "staging" / "extractions" / "bad.json").exists()


def test_extractions_import_reviewed_requires_approval(synthetic_case_copy: Path):
    result = client_for(synthetic_case_copy, dry_run=True).case("synthetic_case").extractions.import_reviewed("p.json")

    assert result.ok is False
    assert result.operation == "extractions.import_reviewed"
    assert result.errors[0].code == SAFETY_BLOCKED


def test_extractions_import_reviewed_plans_after_approval(synthetic_case_copy: Path):
    result = (
        client_for(synthetic_case_copy, dry_run=True)
        .case("synthetic_case")
        .extractions.import_reviewed("p.json", approved=True)
    )

    args = ledger_command_args(result.diagnostics["command"])
    assert result.ok is True
    assert ledger_subcommand(result.diagnostics["command"]) == "import-extraction"
    assert args[1] == str(synthetic_case_copy)
    assert args[2].endswith("staging/extractions/p.json")


def test_extractions_import_reviewed_rejects_path_like_packet_names(synthetic_case_copy: Path):
    result = (
        client_for(synthetic_case_copy, dry_run=True)
        .case("synthetic_case")
        .extractions.import_reviewed("../records/claims.jsonl", approved=True)
    )

    assert result.ok is False
    assert result.errors[0].code == INVALID_INPUT


def test_extractions_ner_suggest_plans_lead_only_candidates(synthetic_case_copy: Path):
    result = client_for(synthetic_case_copy, dry_run=True).case("synthetic_case").extractions.ner_suggest(
        source_id="SDEMO0001",
        limit=5,
    )

    args = ledger_command_args(result.diagnostics["command"])
    assert result.ok is True
    assert result.operation == "extractions.ner_suggest"
    assert args[:2] == ["ner-suggest", str(synthetic_case_copy)]
    assert args[args.index("--source-id") + 1] == "SDEMO0001"
    assert args[args.index("--limit") + 1] == "5"


def test_extractions_ner_suggest_validates_limit(synthetic_case_copy: Path):
    result = client_for(synthetic_case_copy).case("synthetic_case").extractions.ner_suggest(limit=0)

    assert result.ok is False
    assert result.errors[0].code == INVALID_INPUT


def test_extractions_read_missing_packet_returns_sdk_error(synthetic_case_copy: Path):
    result = client_for(synthetic_case_copy).case("synthetic_case").extractions.read("missing.json")

    assert result.ok is False
    assert result.operation == "extractions.read"
    assert result.errors[0].code == INVALID_INPUT


def test_extractions_import_does_not_write_canonical_records_in_dry_run(synthetic_case_copy: Path):
    before = (synthetic_case_copy / "records" / "claims.jsonl").read_text(encoding="utf-8")

    result = (
        client_for(synthetic_case_copy, dry_run=True)
        .case("synthetic_case")
        .extractions.import_reviewed("p.json", approved=True)
    )

    assert result.ok is True
    assert json.loads(json.dumps(result.to_dict()))["operation"] == "extractions.import_reviewed"
    assert (synthetic_case_copy / "records" / "claims.jsonl").read_text(encoding="utf-8") == before
