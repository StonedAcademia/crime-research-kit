from tests.runtime.integration.commands.link_names.helpers import append_event, append_source, assert_unique_ids, load_tcr


def test_link_names_writes_private_unverified_co_mentions(tmp_path):
    tcr = load_tcr()
    case_dir = tmp_path / "case"
    tcr.main(["init-case", str(case_dir), "--title", "Synthetic Link Case"])
    append_source(
        tcr,
        case_dir,
        "STEST0001",
        "seed.txt",
        "Demo Leader and Demo Witness were both mentioned in a report about the harbor meeting.",
    )
    tcr.append_jsonl(
        tcr.record_path(case_dir, "entities"),
        {
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
        },
    )
    append_event(tcr, case_dir, "EVTEST0001", ["STEST0001"], ["EDEMO_LEADER"])
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
    candidate = next(entity for entity in tcr.read_jsonl(tcr.record_path(case_dir, "entities")) if entity["name"] == "Demo Witness")
    assert candidate["source_ids"] == []

    append_source(tcr, case_dir, "STEST0002", "second.txt", "Demo Witness was later mentioned in a sourced report.")
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
    append_source(tcr, case_dir, "STEST0003", "aliases.txt", "Demo Witness and D. Witness refer to the same name-list target.")
    append_event(tcr, case_dir, "EVTEST0003", ["STEST0003"])
    names_file = tmp_path / "names.txt"
    names_file.write_text("Demo Witness|Witness\nWitness|D. Witness\n", encoding="utf-8")

    tcr.main(["link-names", str(case_dir), "--names-file", str(names_file)])
    tcr.main(["link-names", str(case_dir), "--names-file", str(names_file)])

    entities = tcr.read_jsonl(tcr.record_path(case_dir, "entities"))
    assert [entity["name"] for entity in entities] == ["Demo Witness"]
    assert entities[0]["aliases"] == ["Witness", "D. Witness"]
