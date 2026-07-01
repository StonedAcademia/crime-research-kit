import csv
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TCR_PATH = REPO_ROOT / ".agents/skills/truecrime-cult-research/scripts/tcr.py"


def load_tcr():
    spec = importlib.util.spec_from_file_location("tcr", TCR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def append_source(tcr, case_dir):
    tcr.append_jsonl(tcr.record_path(case_dir, "sources"), {
        "source_id": "SCHART",
        "title": "Synthetic chart source",
        "source_type": "news_article",
        "author": "Demo Reporter",
        "publisher": "Demo Daily",
        "date_published": "1970-01-01",
        "date_accessed": "2026-06-30",
        "url": "https://example.test/chart",
        "archive_url": None,
        "raw_path": None,
        "text_path": None,
        "reliability_grade": "B",
        "independence_group": "Demo Daily",
        "notes": "Synthetic chart source.",
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
        "source_ids": ["SCHART"],
        "claim_ids": ["C_CHART"],
        "public_export": public,
        "notes": "Synthetic person.",
    })


def append_claim(tcr, case_dir, public=True):
    tcr.append_jsonl(tcr.record_path(case_dir, "claims"), {
        "claim_id": "C_CHART",
        "claim": "Synthetic chart claim.",
        "claim_type": "event",
        "status": "single_source",
        "confidence": 0.7,
        "source_ids": ["SCHART"],
        "contradicts": [],
        "supports": [],
        "privacy_review": "clear" if public else "needs_review",
        "public_export": public,
        "notes": "Synthetic chart claim.",
    })


def append_event(tcr, case_dir):
    tcr.append_jsonl(tcr.record_path(case_dir, "events"), {
        "event_id": "EV_CHART_ELAN",
        "title": "Elan School opened",
        "event_type": "institution_opening",
        "start_date": "1970",
        "end_date": None,
        "date_precision": "year",
        "place_ids": [],
        "entity_ids": ["E_PUBLIC_A", "E_PUBLIC_B", "E_PRIVATE"],
        "artifact_ids": [],
        "claim_ids": ["C_CHART"],
        "source_ids": ["SCHART"],
        "confidence": 0.7,
        "status": "single_source",
        "public_export": True,
        "notes": "Synthetic chart event.",
    })


def append_relationship(tcr, case_dir):
    tcr.append_jsonl(tcr.record_path(case_dir, "relationships"), {
        "rel_id": "R_CHART",
        "src_entity_id": "E_PUBLIC_A",
        "dst_entity_id": "E_PUBLIC_B",
        "relation_type": "co_participant_in_event",
        "start_date": "1970",
        "end_date": None,
        "claim_ids": ["C_CHART"],
        "source_ids": ["SCHART"],
        "confidence": 0.7,
        "status": "single_source",
        "public_export": True,
        "notes": "Synthetic chart relationship.",
    })


def test_export_case_charts_writes_public_people_graph_and_subcase_timeline(tmp_path):
    tcr = load_tcr()
    case_dir = tmp_path / "case"
    tcr.main(["init-case", str(case_dir), "--title", "Chart Case"])
    append_source(tcr, case_dir)
    append_person(tcr, case_dir, "E_PUBLIC_A", "Public A")
    append_person(tcr, case_dir, "E_PUBLIC_B", "Public B")
    append_person(tcr, case_dir, "E_PRIVATE", "Private Person", public=False)
    append_claim(tcr, case_dir)
    append_event(tcr, case_dir)
    append_relationship(tcr, case_dir)

    out = tmp_path / "charts"
    tcr.main(["export-case-charts", str(case_dir), "--out-dir", str(out)])

    assert (out / "people_graph.html").exists()
    assert (out / "subcase_timelines.html").exists()
    graph_html = (out / "people_graph.html").read_text(encoding="utf-8")
    assert "Evidence-weighted people graph" in graph_html
    assert "Graph Groups" in graph_html

    nodes = read_csv(out / "people_nodes.csv")
    edges = read_csv(out / "people_edges.csv")
    timelines = read_csv(out / "subcase_timelines.csv")

    assert [row["entity_id"] for row in nodes] == ["E_PUBLIC_A", "E_PUBLIC_B"]
    assert len(edges) == 1
    assert edges[0]["connection_types"] == "co_participant_in_event;shared_event"
    assert timelines[0]["subcase_id"] == "elan_tti"


def test_export_case_charts_include_private_adds_internal_people(tmp_path):
    tcr = load_tcr()
    case_dir = tmp_path / "case"
    tcr.main(["init-case", str(case_dir), "--title", "Chart Case Internal"])
    append_source(tcr, case_dir)
    append_person(tcr, case_dir, "E_PUBLIC_A", "Public A")
    append_person(tcr, case_dir, "E_PRIVATE", "Private Person", public=False)
    append_claim(tcr, case_dir)
    append_event(tcr, case_dir)

    out = tmp_path / "charts"
    tcr.main(["export-case-charts", str(case_dir), "--out-dir", str(out), "--include-private"])

    nodes = read_csv(out / "people_nodes.csv")
    edges = read_csv(out / "people_edges.csv")

    assert {row["entity_id"] for row in nodes} == {"E_PUBLIC_A", "E_PRIVATE"}
    assert len(edges) == 1
