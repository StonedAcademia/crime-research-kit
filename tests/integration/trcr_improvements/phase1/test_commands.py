import hashlib
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


def test_phase1_commands_and_templates_are_registered(tmp_path):
    tcr = load_tcr()
    choices = subcommand_parsers(tcr)
    assert {"preserve-source", "resolve-identities", "audit-contradictions"} <= set(choices)

    template_choices = option_choices(tcr, "draft-extraction", "--template")
    assert {
        "legal-court",
        "identity-resolution",
        "source-capture",
        "claim-contradiction",
    } <= template_choices

    case_dir = init_case(tcr, tmp_path, title="Phase 1 Template Case")
    append_source(
        tcr,
        case_dir,
        "S_LEGAL",
        filename="legal.txt",
        text="The docket entry says the court entered an order after the hearing.",
    )
    tcr.main([
        "draft-extraction",
        str(case_dir),
        "S_LEGAL",
        "--template",
        "legal-court",
        "--excerpt-chars",
        "120",
    ])
    packet = json.loads((case_dir / "staging" / "extractions" / "S_LEGAL_extraction.json").read_text(encoding="utf-8"))
    packet_text = json.dumps(packet).lower()
    assert packet["extraction_template"] == "legal-court"
    assert "court_finding" in packet_text
    assert "docket_item" in packet_text


def test_preserve_source_hashes_existing_artifacts_and_updates_source(tmp_path):
    tcr = load_tcr()
    case_dir = init_case(tcr, tmp_path, title="Source Preservation Case")
    raw_path = case_dir / "raw" / "downloads" / "capture.html"
    text_path = case_dir / "raw" / "sources" / "capture.txt"
    raw_path.write_bytes(b"<html><title>Capture</title><p>Record</p></html>")
    text_path.write_text("Capture Record", encoding="utf-8")
    tcr.append_jsonl(tcr.record_path(case_dir, "sources"), {
        "source_id": "S_CAPTURE",
        "title": "Capture source",
        "source_type": "news_article",
        "author": None,
        "publisher": "Example",
        "date_published": "1978-04-12",
        "date_accessed": "2026-06-30",
        "url": "https://example.test/capture",
        "archive_url": None,
        "raw_path": "raw/downloads/capture.html",
        "text_path": "raw/sources/capture.txt",
        "reliability_grade": "B",
        "independence_group": None,
        "notes": "Synthetic source for preservation.",
        "public_export": True,
    })

    tcr.main([
        "preserve-source",
        str(case_dir),
        "S_CAPTURE",
        "--archive-url",
        "https://web.archive.test/capture",
    ])

    source = tcr.read_jsonl(tcr.record_path(case_dir, "sources"))[0]
    assert source["preservation_status"] == "captured"
    assert source["archive_url"] == "https://web.archive.test/capture"
    assert source["raw_sha256"] == hashlib.sha256(raw_path.read_bytes()).hexdigest()
    assert source["text_sha256"] == hashlib.sha256(text_path.read_bytes()).hexdigest()
    report = case_dir / "exports" / "source_preservation" / "S_CAPTURE.json"
    assert report.exists()
    assert json.loads(report.read_text(encoding="utf-8"))["preservation_status"] == "captured"


def test_resolve_identities_reports_candidates_without_merging(tmp_path):
    tcr = load_tcr()
    case_dir = init_case(tcr, tmp_path, title="Identity Resolution Case")
    append_source(tcr, case_dir, "SA")
    append_entity(tcr, case_dir, "E_JANE_A", name="Jane Doe", aliases=["J. Doe"])
    append_entity(tcr, case_dir, "E_JANE_B", name="Jane Doe", aliases=["Jane A. Doe"])

    tcr.main(["resolve-identities", str(case_dir)])

    rows = tcr.read_jsonl(tcr.record_path(case_dir, "entities"))
    assert [row["entity_id"] for row in rows] == ["E_JANE_A", "E_JANE_B"]
    report_path = case_dir / "staging" / "candidates" / f"identity_resolution_{tcr.today()}.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["candidate_count"] == 1
    assert report["candidates"][0]["recommendation"] == "human_review_required_before_merge"
    assert sorted(record["entity_id"] for record in report["candidates"][0]["records"]) == ["E_JANE_A", "E_JANE_B"]


def test_audit_contradictions_reports_explicit_conflicts(tmp_path):
    tcr = load_tcr()
    case_dir = init_case(tcr, tmp_path, title="Contradiction Audit Case")
    append_source(tcr, case_dir, "SA")
    append_source(tcr, case_dir, "SB", publisher="Court")
    append_claim(
        tcr,
        case_dir,
        "C_ALLEGATION",
        ["SA"],
        claim="A filing alleged Jane Doe attended the meeting.",
        assertion_type="allegation",
        contradicts=["C_DENIAL"],
        status="single_source",
    )
    append_claim(
        tcr,
        case_dir,
        "C_DENIAL",
        ["SB"],
        claim="A court order stated Jane Doe did not attend the meeting.",
        assertion_type="court_finding",
        status="verified",
    )

    tcr.main(["audit-contradictions", str(case_dir), "--min-overlap", "0.2"])

    report = json.loads((case_dir / "exports" / "claim_contradiction_audit.json").read_text(encoding="utf-8"))
    assert report["flag_count"] >= 1
    assert report["summary"]["explicit_contradiction"] == 1
    assert {"C_ALLEGATION", "C_DENIAL"} == set(report["flags"][0]["claim_ids"])
