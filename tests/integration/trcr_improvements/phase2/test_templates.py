import json

from tests.integration.trcr_improvements.helpers import (
    append_source,
    init_case,
    load_tcr,
    option_choices,
    subcommand_parsers,
)


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
