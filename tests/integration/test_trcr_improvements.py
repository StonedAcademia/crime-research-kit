import importlib.util
import hashlib
import json
from pathlib import Path

import pytest

from tests.helpers import KIT_ROOT, TCR_PATH

def load_tcr():
    spec = importlib.util.spec_from_file_location("tcr", TCR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def subcommand_parsers(tcr):
    parser = tcr.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if choices and "init-case" in choices:
            return choices
    return {}


def require_command(tcr, *names):
    choices = subcommand_parsers(tcr)
    for name in names:
        if name in choices:
            return name
    pytest.xfail(f"CLI command not implemented yet: one of {', '.join(names)}")


def command_options(tcr, command):
    parser = subcommand_parsers(tcr)[command]
    return {
        option
        for action in parser._actions
        for option in getattr(action, "option_strings", [])
    }


def option_choices(tcr, command, option):
    parser = subcommand_parsers(tcr)[command]
    for action in parser._actions:
        if option in getattr(action, "option_strings", []):
            return set(action.choices or [])
    return set()


def report_text(case_dir, captured, *name_terms):
    chunks = [captured.out, captured.err]
    for path in case_dir.rglob("*"):
        if not path.is_file():
            continue
        lowered = path.name.lower()
        if all(term in lowered for term in name_terms):
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def init_case(tcr, tmp_path, title="Improvement Coverage Case"):
    case_dir = tmp_path / "case"
    tcr.main(["init-case", str(case_dir), "--title", title])
    return case_dir


def append_source(
    tcr,
    case_dir,
    source_id,
    *,
    publisher="Demo Daily",
    independence_group=None,
    source_type="news_article",
    filename=None,
    text=None,
    public_export=True,
):
    text_path = None
    if filename:
        path = case_dir / "raw" / "sources" / filename
        path.write_text(text or "", encoding="utf-8")
        text_path = f"raw/sources/{filename}"
    tcr.append_jsonl(tcr.record_path(case_dir, "sources"), {
        "source_id": source_id,
        "title": f"Synthetic source {source_id}",
        "source_type": source_type,
        "author": "Demo Reporter",
        "publisher": publisher,
        "date_published": "1978-04-12",
        "date_accessed": "2026-06-30",
        "url": f"https://example.test/{source_id.lower()}",
        "archive_url": None,
        "raw_path": None,
        "text_path": text_path,
        "reliability_grade": "B",
        "independence_group": independence_group,
        "notes": "Synthetic source for TRCR improvement coverage.",
        "public_export": public_export,
    })


def append_claim(tcr, case_dir, claim_id, source_ids, **overrides):
    row = {
        "claim_id": claim_id,
        "claim": f"Synthetic claim {claim_id}",
        "claim_type": "background",
        "status": "single_source",
        "confidence": 0.7,
        "source_ids": source_ids,
        "contradicts": [],
        "supports": [],
        "privacy_review": "clear",
        "public_export": True,
        "notes": "Synthetic claim.",
    }
    row.update(overrides)
    tcr.append_jsonl(tcr.record_path(case_dir, "claims"), row)


def append_entity(tcr, case_dir, entity_id, **overrides):
    row = {
        "entity_id": entity_id,
        "entity_type": "person",
        "name": f"Person {entity_id}",
        "display_name": f"Person {entity_id}",
        "aliases": [],
        "status": "confirmed",
        "role_tags": ["person_mentioned"],
        "privacy_level": "public_figure",
        "living_status": "unknown",
        "source_ids": ["SA"],
        "claim_ids": [],
        "public_export": True,
        "notes": "Synthetic entity.",
    }
    row.update(overrides)
    tcr.append_jsonl(tcr.record_path(case_dir, "entities"), row)


def validate_schema(schema_name, row):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(next((KIT_ROOT / "docs" / "schemas").rglob(schema_name)).read_text(encoding="utf-8"))
    jsonschema.validate(instance=row, schema=schema)


def test_public_schemas_validate_independence_groups_and_bridge_classes():
    validate_schema("source.schema.json", {
        "source_id": "SA",
        "title": "Independent source",
        "source_type": "news_article",
        "author": "Demo Reporter",
        "publisher": "Demo Daily",
        "date_published": "1978-04-12",
        "date_accessed": "2026-06-30",
        "url": "https://example.test/a",
        "archive_url": None,
        "raw_path": None,
        "text_path": None,
        "content_type": "text/html",
        "capture_method": "ingest_url",
        "capture_timestamp": "2026-06-30T00:00:00+00:00",
        "preservation_checked_at": "2026-06-30T00:00:01+00:00",
        "raw_sha256": "a" * 64,
        "text_sha256": "b" * 64,
        "raw_size_bytes": 123,
        "text_size_bytes": 45,
        "preservation_status": "captured",
        "preservation_warnings": [],
        "reliability_grade": "B",
        "independence_group": "Demo Publishing Group",
        "notes": "Synthetic source.",
        "public_export": True,
    })
    validate_schema("relationship.schema.json", {
        "rel_id": "R_A",
        "src_entity_id": "E_A",
        "dst_entity_id": "E_B",
        "relation_type": "worked_for",
        "relationship_class": "personnel_bridge",
        "start_date": "1978",
        "end_date": None,
        "claim_ids": ["C_A"],
        "source_ids": ["SA"],
        "confidence": 0.7,
        "status": "single_source",
        "public_export": True,
        "notes": "Synthetic relationship.",
    })
    validate_schema("event_link.schema.json", {
        "event_link_id": "EL_A",
        "entity_id": "E_A",
        "event_id": "EV_A",
        "relation_type": "participant",
        "relationship_class": "hypothesis_requires_more_sources",
        "basis": "Synthetic event link.",
        "claim_ids": ["C_A"],
        "source_ids": ["SA"],
        "confidence": 0.4,
        "status": "unverified",
        "public_export": False,
        "notes": "Synthetic event link.",
    })


def test_public_schemas_reject_unknown_bridge_class():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(next((KIT_ROOT / "docs" / "schemas").rglob("relationship.schema.json")).read_text(encoding="utf-8"))
    invalid_relationship = {
        "rel_id": "R_BAD",
        "src_entity_id": "E_A",
        "dst_entity_id": "E_B",
        "relation_type": "co_mentioned_with",
        "relationship_class": "rumor_bridge",
        "claim_ids": [],
        "source_ids": ["SA"],
        "confidence": 0.3,
        "status": "unverified",
        "public_export": False,
        "notes": "Synthetic invalid relationship.",
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_relationship, schema=schema)


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

    tcr.main([
        "draft-extraction",
        str(case_dir),
        "S_CORP",
        template_flag,
        "corporate",
        "--excerpt-chars",
        "120",
    ])
    corporate_packet = json.loads(
        (case_dir / "staging" / "extractions" / "S_CORP_extraction.json").read_text(encoding="utf-8")
    )
    corporate_text = json.dumps(corporate_packet).lower()
    assert corporate_packet["extraction_template"] == "corporate"
    assert "corporate" in corporate_text
    assert "officer_or_director_role" in corporate_text
    assert "source_spans" in corporate_packet
    assert "claims" in corporate_packet

    tcr.main([
        "draft-extraction",
        str(case_dir),
        "S_EDU",
        template_flag,
        "education",
        "--excerpt-chars",
        "120",
    ])
    education_packet = json.loads(
        (case_dir / "staging" / "extractions" / "S_EDU_extraction.json").read_text(encoding="utf-8")
    )
    education_text = json.dumps(education_packet).lower()
    assert education_packet["extraction_template"] == "education"
    assert "education" in education_text
    assert "attendance_or_enrollment" in education_text
    assert "source_spans" in education_packet
    assert "claims" in education_packet


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


def test_phase2_commands_and_templates_are_registered(tmp_path):
    tcr = load_tcr()
    choices = subcommand_parsers(tcr)
    assert {"plan-public-records", "index-transcript"} <= set(choices)

    template_choices = option_choices(tcr, "draft-extraction", "--template")
    assert {
        "public-records-router",
        "licensing-professional",
        "media-transcript",
        "property-location",
    } <= template_choices

    case_dir = init_case(tcr, tmp_path, title="Phase 2 Template Case")
    append_source(
        tcr,
        case_dir,
        "S_LICENSE",
        filename="license.txt",
        text="The board lookup listed license status and a disciplinary order.",
    )
    tcr.main([
        "draft-extraction",
        str(case_dir),
        "S_LICENSE",
        "--template",
        "licensing-professional",
        "--excerpt-chars",
        "120",
    ])
    packet = json.loads((case_dir / "staging" / "extractions" / "S_LICENSE_extraction.json").read_text(encoding="utf-8"))
    packet_text = json.dumps(packet).lower()
    assert packet["extraction_template"] == "licensing-professional"
    assert "license_status" in packet_text
    assert "disciplinary_action" in packet_text


def test_plan_public_records_writes_lane_report_without_evidence_rows(tmp_path):
    tcr = load_tcr()
    case_dir = init_case(tcr, tmp_path, title="Public Records Router Case")

    tcr.main([
        "plan-public-records",
        str(case_dir),
        "--subject",
        "Jane Doe professional license and property records",
        "--lane",
        "licensing-professional",
        "--lane",
        "property-location",
    ])

    report_path = next((case_dir / "staging" / "candidates").glob(f"public_records_plan_jane_doe_professional_license*_{tcr.today()}.json"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert [lane["lane"] for lane in report["lanes"]] == ["licensing-professional", "property-location"]
    assert report["lanes"][0]["skill"] == "licensing-professional-records"
    assert "lead map" in report["policy"]
    assert tcr.read_jsonl(tcr.record_path(case_dir, "claims")) == []


def test_missing_persons_and_geographical_location_templates_are_registered(tmp_path):
    tcr = load_tcr()
    template_choices = option_choices(tcr, "draft-extraction", "--template")
    assert {"missing-persons", "geographical-location"} <= template_choices

    case_dir = init_case(tcr, tmp_path, title="Missing Geography Template Case")
    append_source(
        tcr,
        case_dir,
        "S_MISSING",
        source_type="government_record",
        filename="missing.txt",
        text="The public bulletin said Jane Doe was last seen near Riverside Park and was later located.",
    )
    tcr.main([
        "draft-extraction",
        str(case_dir),
        "S_MISSING",
        "--template",
        "missing-persons",
        "--excerpt-chars",
        "120",
    ])
    missing_packet = json.loads((case_dir / "staging" / "extractions" / "S_MISSING_extraction.json").read_text(encoding="utf-8"))
    missing_text = json.dumps(missing_packet).lower()
    assert missing_packet["extraction_template"] == "missing-persons"
    assert "last_seen_or_last_contact" in missing_text
    assert "possible_match" in missing_text

    append_source(
        tcr,
        case_dir,
        "S_MAP",
        source_type="official_report",
        filename="map.txt",
        text="Exhibit 4 mapped the evidence item at a route segment near the station.",
    )
    tcr.main([
        "draft-extraction",
        str(case_dir),
        "S_MAP",
        "--template",
        "geographical-location",
        "--excerpt-chars",
        "120",
    ])
    geo_packet = json.loads((case_dir / "staging" / "extractions" / "S_MAP_extraction.json").read_text(encoding="utf-8"))
    geo_text = json.dumps(geo_packet).lower()
    assert geo_packet["extraction_template"] == "geographical-location"
    assert "evidence_item_location" in geo_text
    assert "precision_values" in geo_text


def test_plan_public_records_supports_missing_and_geographical_lanes(tmp_path):
    tcr = load_tcr()
    case_dir = init_case(tcr, tmp_path, title="Missing Geography Router Case")

    tcr.main([
        "plan-public-records",
        str(case_dir),
        "--subject",
        "Jane Doe missing person last seen route map",
        "--lane",
        "geographical-location",
        "--lane",
        "missing-persons",
    ])

    report_path = next((case_dir / "staging" / "candidates").glob(f"public_records_plan_jane_doe_missing_person*_{tcr.today()}.json"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert [lane["lane"] for lane in report["lanes"]] == ["geographical-location", "missing-persons"]
    assert report["lanes"][0]["skill"] == "geographical-location-intelligence"
    assert report["lanes"][1]["skill"] == "missing-persons-case"
    assert report["lanes"][1]["template"] == "missing-persons"
    assert tcr.read_jsonl(tcr.record_path(case_dir, "claims")) == []


def test_index_transcript_writes_timestamp_and_speaker_candidates(tmp_path):
    tcr = load_tcr()
    case_dir = init_case(tcr, tmp_path, title="Transcript Index Case")
    append_source(
        tcr,
        case_dir,
        "S_TRANSCRIPT",
        source_type="interview",
        filename="transcript.txt",
        text="\n".join([
            "00:01 HOST: Welcome to the interview.",
            "00:05 GUEST: I saw the meeting begin after noon.",
            "NARRATOR: The program later published a correction.",
        ]),
    )

    tcr.main(["index-transcript", str(case_dir), "S_TRANSCRIPT"])

    report_path = case_dir / "staging" / "candidates" / f"transcript_index_S_TRANSCRIPT_{tcr.today()}.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["segment_count"] == 3
    assert report["segments"][0]["timestamp"] == "00:01"
    assert report["segments"][0]["speaker"] == "HOST"
    assert report["segments"][1]["timestamp_seconds"] == 5
    assert set(report["speakers"]) == {"GUEST", "HOST", "NARRATOR"}


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
