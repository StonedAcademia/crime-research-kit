import json

import pytest

from tests.integration.trcr_improvements.helpers import (
    append_claim,
    append_entity,
    append_source,
    command_options,
    init_case,
    load_tcr,
    option_choices,
    report_text,
    require_command,
)


def test_dedupe_command_reports_duplicate_candidates_without_mutating_rows(tmp_path, capsys):
    tcr = load_tcr()
    case_dir = init_case(tcr, tmp_path)
    append_source(tcr, case_dir, "SA")
    append_entity(tcr, case_dir, "E_DUP", name="Duplicate Person")
    append_entity(tcr, case_dir, "E_DUP", name="Duplicate Person")

    command = require_command(tcr, "dedupe")
    tcr.main([command, str(case_dir)])

    rows = tcr.read_jsonl(tcr.record_path(case_dir, "entities"))
    assert [row["entity_id"] for row in rows].count("E_DUP") == 2
    text = report_text(case_dir, capsys.readouterr(), "dedupe")
    assert "E_DUP" in text
    assert "duplicate" in text.lower()
    assert "entities" in text.lower()
    assert "does not merge or delete evidence rows" in text


def test_audit_public_export_flags_private_people_and_weak_claims(tmp_path, capsys):
    tcr = load_tcr()
    case_dir = init_case(tcr, tmp_path)
    append_source(tcr, case_dir, "SA")
    append_entity(
        tcr,
        case_dir,
        "E_PRIVATE",
        name="Private Witness",
        display_name="Private Witness",
        privacy_level="private_person",
        living_status="living",
        claim_ids=["C_WEAK"],
        public_export=True,
    )
    append_claim(
        tcr,
        case_dir,
        "C_WEAK",
        ["SA"],
        status="unverified",
        confidence=0.25,
        privacy_review="needs_review",
        public_export=True,
    )

    command = require_command(tcr, "audit-public-export")
    try:
        tcr.main([command, str(case_dir)])
    except SystemExit as exc:
        assert exc.code in (1, "1")

    text = report_text(case_dir, capsys.readouterr(), "public", "export")
    assert "E_PRIVATE" in text
    assert "private_person" in text
    assert "C_WEAK" in text
    assert "needs_review" in text or "unverified" in text


def test_source_independence_command_reports_same_group_claims(tmp_path, capsys):
    tcr = load_tcr()
    case_dir = init_case(tcr, tmp_path)
    append_source(tcr, case_dir, "SA", publisher="Wire A", independence_group="Newswire")
    append_source(tcr, case_dir, "SB", publisher="Wire B", independence_group="Newswire")
    append_source(tcr, case_dir, "SC", publisher="Local Archive", independence_group="Local Archive")
    append_claim(tcr, case_dir, "C_SHARED_GROUP", ["SA", "SB"], status="corroborated")
    append_claim(tcr, case_dir, "C_INDEPENDENT", ["SA", "SC"], status="corroborated")

    command = require_command(tcr, "source-independence", "audit-source-independence")
    tcr.main([command, str(case_dir)])

    text = report_text(case_dir, capsys.readouterr(), "source", "independence")
    assert "C_SHARED_GROUP" in text
    assert "Newswire" in text
    assert "SA;SB" in text
    assert "C_INDEPENDENT" not in text


def test_draft_extraction_writes_topic_specific_templates(tmp_path):
    tcr = load_tcr()
    case_dir = init_case(tcr, tmp_path)
    append_source(
        tcr,
        case_dir,
        "S_CORP",
        filename="corporate.txt",
        text="The filing listed a corporation, its director, and a regulatory action.",
    )
    append_source(
        tcr,
        case_dir,
        "S_EDU",
        filename="education.txt",
        text="The alumni notice described enrollment, a degree, and an academic appointment.",
    )

    draft_options = command_options(tcr, "draft-extraction")
    template_flag = next((flag for flag in ("--topic", "--template") if flag in draft_options), None)
    if not template_flag:
        pytest.xfail("draft-extraction topic/template option is not implemented yet")
    choices = option_choices(tcr, "draft-extraction", template_flag)
    if choices and not {"corporate", "education"} <= choices:
        pytest.xfail("corporate and education extraction templates are not implemented yet")

    tcr.main(["draft-extraction", str(case_dir), "S_CORP", template_flag, "corporate", "--excerpt-chars", "120"])
    corporate_packet = json.loads(
        (case_dir / "staging" / "extractions" / "S_CORP_extraction.json").read_text(encoding="utf-8")
    )
    corporate_text = json.dumps(corporate_packet).lower()
    assert corporate_packet["extraction_template"] == "corporate"
    assert "corporate" in corporate_text
    assert "officer_or_director_role" in corporate_text
    assert "source_spans" in corporate_packet
    assert "claims" in corporate_packet

    tcr.main(["draft-extraction", str(case_dir), "S_EDU", template_flag, "education", "--excerpt-chars", "120"])
    education_packet = json.loads(
        (case_dir / "staging" / "extractions" / "S_EDU_extraction.json").read_text(encoding="utf-8")
    )
    education_text = json.dumps(education_packet).lower()
    assert education_packet["extraction_template"] == "education"
    assert "education" in education_text
    assert "attendance_or_enrollment" in education_text
    assert "source_spans" in education_packet
    assert "claims" in education_packet
