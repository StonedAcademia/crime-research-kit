import csv

from tests.helpers import load_ledger_cli


def load_tcr():
    return load_ledger_cli()


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def append_source(tcr, case_dir, source_id, grade="B"):
    tcr.append_jsonl(tcr.record_path(case_dir, "sources"), {
        "source_id": source_id,
        "title": f"Synthetic source {source_id}",
        "source_type": "news_article",
        "author": "Demo Reporter",
        "publisher": "Demo Daily",
        "date_published": "1970-01-01",
        "date_accessed": "2026-06-30",
        "url": f"https://example.test/{source_id.lower()}",
        "archive_url": None,
        "raw_path": None,
        "text_path": None,
        "reliability_grade": grade,
        "independence_group": "Demo Daily",
        "notes": "Synthetic visual source.",
        "public_export": True,
    })


def append_person(tcr, case_dir, entity_id, name, public=True):
    tcr.append_jsonl(tcr.record_path(case_dir, "entities"), {
        "entity_id": entity_id,
        "entity_type": "person",
        "name": name,
        "display_name": name,
        "aliases": [],
        "status": "confirmed" if public else "candidate",
        "role_tags": ["person_mentioned"],
        "privacy_level": "public_figure" if public else "unknown",
        "living_status": "unknown",
        "source_ids": ["SA"],
        "claim_ids": ["C_A"],
        "public_export": public,
        "notes": "Synthetic person.",
    })


def build_visual_case(tmp_path):
    tcr = load_tcr()
    case_dir = tmp_path / "case"
    tcr.main(["init-case", str(case_dir), "--title", "Visual Case"])
    append_source(tcr, case_dir, "SA", "A")
    append_source(tcr, case_dir, "SB", "B")
    append_person(tcr, case_dir, "E_A", "Public A")
    append_person(tcr, case_dir, "E_B", "Public B")
    append_person(tcr, case_dir, "E_PRIVATE", "Private Person", public=False)
    tcr.append_jsonl(tcr.record_path(case_dir, "claims"), {
        "claim_id": "C_A",
        "claim": "Synthetic claim supported by two sources.",
        "claim_type": "event",
        "status": "corroborated",
        "confidence": 0.85,
        "source_ids": ["SA", "SB"],
        "contradicts": [],
        "supports": [],
        "privacy_review": "clear",
        "public_export": True,
        "notes": "Synthetic claim.",
    })
    tcr.append_jsonl(tcr.record_path(case_dir, "events"), {
        "event_id": "EV_A",
        "title": "Synthetic event",
        "event_type": "timeline_anchor",
        "start_date": "1970",
        "end_date": None,
        "date_precision": "year",
        "place_ids": [],
        "entity_ids": ["E_A", "E_B", "E_PRIVATE"],
        "artifact_ids": [],
        "claim_ids": ["C_A"],
        "source_ids": ["SA"],
        "confidence": 0.8,
        "status": "single_source",
        "public_export": True,
        "notes": "Synthetic event.",
    })
    tcr.append_jsonl(tcr.record_path(case_dir, "event_links"), {
        "event_link_id": "EL_A",
        "event_id": "EV_A",
        "entity_id": "E_A",
        "relation_type": "participant",
        "relationship_class": "personnel_bridge",
        "basis": "Synthetic event link.",
        "claim_ids": ["C_A"],
        "source_ids": ["SA"],
        "confidence": 0.8,
        "status": "single_source",
        "public_export": True,
        "notes": "Synthetic event link.",
    })
    tcr.append_jsonl(tcr.record_path(case_dir, "relationships"), {
        "rel_id": "R_A",
        "src_entity_id": "E_A",
        "dst_entity_id": "E_B",
        "relation_type": "co_participant_in_event",
        "relationship_class": "personnel_bridge",
        "start_date": "1970",
        "end_date": None,
        "claim_ids": ["C_A"],
        "source_ids": ["SA", "SB"],
        "confidence": 0.85,
        "status": "corroborated",
        "public_export": True,
        "notes": "Synthetic relationship.",
    })
    return tcr, case_dir
