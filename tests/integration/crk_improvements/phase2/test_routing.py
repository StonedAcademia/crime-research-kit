import json

from tests.integration.crk_improvements.helpers import append_source, init_case, load_tcr


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
