import json

from tests.integration.trcr_improvements.helpers import (
    append_claim,
    append_entity,
    append_source,
    init_case,
    load_tcr,
    option_choices,
    subcommand_parsers,
)


def test_phase3_commands_and_templates_are_registered(tmp_path):
    tcr = load_tcr()
    choices = subcommand_parsers(tcr)
    assert {"plan-open-records", "review-narrative-readiness", "audit-privacy-redactions"} <= set(choices)
    assert "source-independence" in choices or "audit-source-independence" in choices

    template_choices = option_choices(tcr, "draft-extraction", "--template")
    assert {
        "foia-open-records",
        "narrative-readiness",
        "privacy-redaction",
        "source-independence",
    } <= template_choices

    case_dir = init_case(tcr, tmp_path, title="Phase 3 Template Case")
    append_source(
        tcr,
        case_dir,
        "S_REVIEW",
        filename="review.txt",
        text="The public records request plan listed agency scope, fee status, and appeal deadline.",
    )
    tcr.main([
        "draft-extraction",
        str(case_dir),
        "S_REVIEW",
        "--template",
        "foia-open-records",
        "--excerpt-chars",
        "120",
    ])
    packet = json.loads((case_dir / "staging" / "extractions" / "S_REVIEW_extraction.json").read_text(encoding="utf-8"))
    packet_text = json.dumps(packet).lower()
    assert packet["extraction_template"] == "foia-open-records"
    assert "appeal_deadline" in packet_text
    assert "request_letter" in packet_text


def test_plan_open_records_writes_request_plan_without_evidence_rows(tmp_path):
    tcr = load_tcr()
    case_dir = init_case(tcr, tmp_path, title="Open Records Plan Case")

    tcr.main([
        "plan-open-records",
        str(case_dir),
        "--subject",
        "Jane Doe agency records",
        "--agency",
        "Example Records Office",
        "--jurisdiction",
        "Example State",
        "--date-range",
        "1970-1975",
        "--record",
        "incident logs",
        "--record",
        "public correspondence metadata",
    ])

    report_path = case_dir / "staging" / "candidates" / f"open_records_plan_jane_doe_agency_records_{tcr.today()}.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["agency"] == "Example Records Office"
    assert report["requested_records"] == ["incident logs", "public correspondence metadata"]
    assert "Please exclude or redact private-person contact details" in report["request_text"]
    assert tcr.read_jsonl(tcr.record_path(case_dir, "claims")) == []


def test_review_narrative_readiness_reports_public_blockers(tmp_path):
    tcr = load_tcr()
    case_dir = init_case(tcr, tmp_path, title="Narrative Readiness Case")
    append_source(tcr, case_dir, "SA", publisher="Single Outlet")
    append_claim(
        tcr,
        case_dir,
        "C_ALLEGATION_SINGLE",
        ["SA"],
        claim="A single source alleged Jane Doe attended the meeting.",
        assertion_type="allegation",
        status="single_source",
        privacy_review="clear",
        public_export=True,
    )

    tcr.main(["review-narrative-readiness", str(case_dir), "--require-spans"])

    report = json.loads((case_dir / "exports" / "narrative_readiness_review.json").read_text(encoding="utf-8"))
    assert report["issue_count"] >= 2
    assert report["summary"]["weak_allegation_support"] == 1
    assert report["summary"]["missing_source_spans"] == 1
    assert report["severity_summary"]["blocker"] >= 1


def test_audit_privacy_redactions_reports_private_public_records(tmp_path):
    tcr = load_tcr()
    case_dir = init_case(tcr, tmp_path, title="Privacy Audit Case")
    append_source(tcr, case_dir, "SA")
    append_entity(
        tcr,
        case_dir,
        "E_PRIVATE",
        name="Private Person",
        display_name="Private Person",
        privacy_level="private_person",
        living_status="living",
        notes="Synthetic private record at 123 Main Street.",
        public_export=True,
    )

    tcr.main(["audit-privacy-redactions", str(case_dir), "--warn-only", "--require-redaction-log"])

    report = json.loads((case_dir / "exports" / "privacy_redaction_audit.json").read_text(encoding="utf-8"))
    assert report["issue_count"] >= 2
    assert report["summary"]["private_person_public"] == 1
    assert report["summary"]["missing_redaction_log"] == 1
    assert report["severity_summary"]["blocker"] >= 1
