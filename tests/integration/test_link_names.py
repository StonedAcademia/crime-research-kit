import importlib.util
from pathlib import Path

from tests.helpers import TCR_PATH

def load_tcr():
    spec = importlib.util.spec_from_file_location("tcr", TCR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def append_source(tcr, case_dir, source_id, filename, text):
    text_path = case_dir / "raw" / "sources" / filename
    text_path.write_text(text, encoding="utf-8")
    tcr.append_jsonl(tcr.record_path(case_dir, "sources"), {
        "source_id": source_id,
        "title": f"Synthetic source {source_id}",
        "source_type": "news_article",
        "author": "Demo Reporter",
        "publisher": "Demo Daily",
        "date_published": "1978-04-12",
        "date_accessed": "2026-06-29",
        "url": f"https://example.test/{source_id.lower()}",
        "archive_url": None,
        "raw_path": None,
        "text_path": f"raw/sources/{filename}",
        "reliability_grade": "B",
        "independence_group": None,
        "notes": "Synthetic source for test.",
        "public_export": True,
    })


def append_event(tcr, case_dir, event_id, source_ids, entity_ids=None):
    tcr.append_jsonl(tcr.record_path(case_dir, "events"), {
        "event_id": event_id,
        "title": f"Synthetic event {event_id}",
        "event_type": "meeting",
        "start_date": "1978-04-12",
        "end_date": None,
        "date_precision": "day",
        "place_ids": [],
        "entity_ids": entity_ids or [],
        "artifact_ids": [],
        "claim_ids": [],
        "source_ids": source_ids,
        "confidence": 0.5,
        "status": "single_source",
        "public_export": True,
        "notes": "Synthetic event.",
    })


def assert_unique_ids(rows, id_field):
    values = [row[id_field] for row in rows]
    assert len(values) == len(set(values))


def test_parse_name_entries_supports_aliases_and_files(tmp_path):
    tcr = load_tcr()
    names_file = tmp_path / "names.txt"
    names_file.write_text(
        "\n".join([
            "# ignored",
            "Demo Leader|Leader",
            "Demo Witness|Witness",
            "Demo Leader|Leader",
        ]),
        encoding="utf-8",
    )

    entries = tcr.parse_name_entries(["Inline Person|I.P."], [str(names_file)])

    assert [entry["primary"] for entry in entries] == ["Demo Leader", "Demo Witness", "Inline Person"]
    assert entries[0]["aliases"] == ["Demo Leader", "Leader"]
    assert entries[2]["aliases"] == ["Inline Person", "I.P."]


def test_parse_name_entries_merges_overlapping_aliases(tmp_path):
    tcr = load_tcr()
    names_file = tmp_path / "names.txt"
    names_file.write_text(
        "\n".join([
            "Demo Leader|Leader",
            "Leader|D. Leader",
            "Demo Witness|Witness",
        ]),
        encoding="utf-8",
    )

    entries = tcr.parse_name_entries(["Witness|D. Witness"], [str(names_file)])

    assert [entry["primary"] for entry in entries] == ["Demo Leader", "Demo Witness"]
    assert entries[0]["aliases"] == ["Demo Leader", "Leader", "D. Leader"]
    assert entries[1]["aliases"] == ["Demo Witness", "Witness", "D. Witness"]


def test_link_names_writes_private_unverified_co_mentions(tmp_path):
    tcr = load_tcr()
    case_dir = tmp_path / "case"
    tcr.main(["init-case", str(case_dir), "--title", "Synthetic Link Case"])

    text_path = case_dir / "raw" / "sources" / "seed.txt"
    text_path.write_text(
        "Demo Leader and Demo Witness were both mentioned in a report about the harbor meeting.",
        encoding="utf-8",
    )
    tcr.append_jsonl(tcr.record_path(case_dir, "sources"), {
        "source_id": "STEST0001",
        "title": "Synthetic source",
        "source_type": "news_article",
        "author": "Demo Reporter",
        "publisher": "Demo Daily",
        "date_published": "1978-04-12",
        "date_accessed": "2026-06-29",
        "url": "https://example.test/source",
        "archive_url": None,
        "raw_path": None,
        "text_path": "raw/sources/seed.txt",
        "reliability_grade": "B",
        "independence_group": None,
        "notes": "Synthetic source for test.",
        "public_export": True,
    })
    tcr.append_jsonl(tcr.record_path(case_dir, "entities"), {
        "entity_id": "EDEMO_LEADER",
        "entity_type": "person",
        "name": "Demo Leader",
        "display_name": "Demo Leader",
        "aliases": ["Leader"],
        "status": "confirmed",
        "role_tags": ["person_mentioned"],
        "privacy_level": "public_figure",
        "living_status": "unknown",
        "source_ids": ["STEST0001"],
        "claim_ids": [],
        "public_export": True,
        "notes": "Synthetic entity.",
    })
    tcr.append_jsonl(tcr.record_path(case_dir, "events"), {
        "event_id": "EVTEST0001",
        "title": "Harbor meeting report",
        "event_type": "meeting",
        "start_date": "1978-04-12",
        "end_date": None,
        "date_precision": "day",
        "place_ids": [],
        "entity_ids": ["EDEMO_LEADER"],
        "artifact_ids": [],
        "claim_ids": [],
        "source_ids": ["STEST0001"],
        "confidence": 0.5,
        "status": "single_source",
        "public_export": True,
        "notes": "Synthetic event.",
    })
    names_file = tmp_path / "names.txt"
    names_file.write_text("Demo Leader|Leader\nDemo Witness|Witness\n", encoding="utf-8")

    tcr.main(["link-names", str(case_dir), "--names-file", str(names_file)])

    entities = tcr.read_jsonl(tcr.record_path(case_dir, "entities"))
    candidate = next(entity for entity in entities if entity["name"] == "Demo Witness")
    assert candidate["status"] == "candidate"
    assert candidate["public_export"] is False
    assert candidate["source_ids"] == ["STEST0001"]

    event_links = tcr.read_jsonl(tcr.record_path(case_dir, "event_links"))
    assert {link["entity_id"] for link in event_links} == {"EDEMO_LEADER", candidate["entity_id"]}
    assert {link["relation_type"] for link in event_links} == {"co_mentioned_in_event"}
    assert all(link["status"] == "unverified" for link in event_links)
    assert all(link["public_export"] is False for link in event_links)

    relationships = tcr.read_jsonl(tcr.record_path(case_dir, "relationships"))
    assert any(rel["relation_type"] == "co_mentioned_with" for rel in relationships)
    assert all(rel["public_export"] is False for rel in relationships)

    briefs = list((case_dir / "notes").glob("name_link_research_*.md"))
    assert len(briefs) == 1
    assert "Co-mention is not evidence" in briefs[0].read_text(encoding="utf-8")

    tcr.main(["validate", str(case_dir)])
    tcr.main(["export-manim", str(case_dir), "--include-private"])
    event_links_csv = case_dir / "exports" / "manim" / "event_links.csv"
    assert event_links_csv.exists()
    assert event_links_csv.read_text(encoding="utf-8").startswith("event_link_id,entity_id,event_id")


def test_link_names_rerun_updates_candidate_sources_without_duplicate_rows(tmp_path):
    tcr = load_tcr()
    case_dir = tmp_path / "case"
    tcr.main(["init-case", str(case_dir), "--title", "Synthetic Rerun Case"])
    names_file = tmp_path / "names.txt"
    names_file.write_text("Demo Witness|Witness\n", encoding="utf-8")

    tcr.main(["link-names", str(case_dir), "--names-file", str(names_file)])
    initial_entities = tcr.read_jsonl(tcr.record_path(case_dir, "entities"))
    candidate = next(entity for entity in initial_entities if entity["name"] == "Demo Witness")
    assert candidate["source_ids"] == []

    append_source(
        tcr,
        case_dir,
        "STEST0002",
        "second.txt",
        "Demo Witness was later mentioned in a sourced report.",
    )
    append_event(tcr, case_dir, "EVTEST0002", ["STEST0002"])

    tcr.main(["link-names", str(case_dir), "--names-file", str(names_file)])
    counts_after_update = {
        record_name: len(tcr.read_jsonl(tcr.record_path(case_dir, record_name)))
        for record_name in ["entities", "event_links", "relationships"]
    }

    tcr.main(["link-names", str(case_dir), "--names-file", str(names_file)])

    entities = tcr.read_jsonl(tcr.record_path(case_dir, "entities"))
    candidates = [entity for entity in entities if entity["name"] == "Demo Witness"]
    assert len(candidates) == 1
    assert candidates[0]["source_ids"] == ["STEST0002"]

    assert counts_after_update == {
        record_name: len(tcr.read_jsonl(tcr.record_path(case_dir, record_name)))
        for record_name in ["entities", "event_links", "relationships"]
    }
    assert_unique_ids(entities, "entity_id")
    assert_unique_ids(tcr.read_jsonl(tcr.record_path(case_dir, "event_links")), "event_link_id")
    assert_unique_ids(tcr.read_jsonl(tcr.record_path(case_dir, "relationships")), "rel_id")


def test_link_names_merges_duplicate_name_inputs_before_writing_candidates(tmp_path):
    tcr = load_tcr()
    case_dir = tmp_path / "case"
    tcr.main(["init-case", str(case_dir), "--title", "Synthetic Duplicate Alias Case"])
    append_source(
        tcr,
        case_dir,
        "STEST0003",
        "aliases.txt",
        "Demo Witness and D. Witness refer to the same name-list target in this synthetic text.",
    )
    append_event(tcr, case_dir, "EVTEST0003", ["STEST0003"])
    names_file = tmp_path / "names.txt"
    names_file.write_text(
        "\n".join([
            "Demo Witness|Witness",
            "Witness|D. Witness",
        ]),
        encoding="utf-8",
    )

    tcr.main(["link-names", str(case_dir), "--names-file", str(names_file)])
    tcr.main(["link-names", str(case_dir), "--names-file", str(names_file)])

    entities = tcr.read_jsonl(tcr.record_path(case_dir, "entities"))
    assert [entity["name"] for entity in entities] == ["Demo Witness"]
    assert entities[0]["aliases"] == ["Witness", "D. Witness"]
    assert entities[0]["source_ids"] == ["STEST0003"]
    assert_unique_ids(entities, "entity_id")
    assert_unique_ids(tcr.read_jsonl(tcr.record_path(case_dir, "event_links")), "event_link_id")
