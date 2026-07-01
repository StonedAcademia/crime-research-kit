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


def append_source(tcr, case_dir, source_id, grade, publisher):
    tcr.append_jsonl(tcr.record_path(case_dir, "sources"), {
        "source_id": source_id,
        "title": f"Source {source_id}",
        "source_type": "news_article",
        "author": "Demo Reporter",
        "publisher": publisher,
        "date_published": "1970-01-01",
        "date_accessed": "2026-06-30",
        "url": f"https://example.test/{source_id.lower()}",
        "archive_url": None,
        "raw_path": None,
        "text_path": None,
        "reliability_grade": grade,
        "independence_group": publisher,
        "notes": "Synthetic timeline source.",
        "public_export": True,
    })


def append_claim(tcr, case_dir, claim_id, source_ids, public=True, status="single_source"):
    tcr.append_jsonl(tcr.record_path(case_dir, "claims"), {
        "claim_id": claim_id,
        "claim": f"Synthetic claim {claim_id}",
        "claim_type": "background",
        "status": status,
        "confidence": 0.7,
        "source_ids": source_ids,
        "contradicts": [],
        "supports": [],
        "privacy_review": "clear" if public else "needs_review",
        "public_export": public,
        "notes": "Synthetic timeline claim.",
    })


def append_event(tcr, case_dir, event_id, claim_ids, source_ids):
    tcr.append_jsonl(tcr.record_path(case_dir, "events"), {
        "event_id": event_id,
        "title": f"Synthetic event {event_id}",
        "event_type": "timeline_anchor",
        "start_date": "1970-01-01",
        "end_date": None,
        "date_precision": "day",
        "place_ids": [],
        "entity_ids": [],
        "artifact_ids": [],
        "claim_ids": claim_ids,
        "source_ids": source_ids,
        "confidence": 0.7,
        "status": "single_source",
        "public_export": True,
        "notes": "Synthetic timeline event.",
    })


def test_export_timeline_writes_public_cross_case_outputs(tmp_path):
    tcr = load_tcr()
    cases_root = tmp_path / "cases"
    case_dir = cases_root / "case_a"
    tcr.main(["init-case", str(case_dir), "--title", "Case A"])

    append_source(tcr, case_dir, "SA", "A", "Official Archive")
    append_source(tcr, case_dir, "SB", "B", "Independent Daily")
    append_claim(tcr, case_dir, "C_PUBLIC", ["SA", "SB"])
    append_claim(tcr, case_dir, "C_PRIVATE", ["SA"], public=False, status="disputed")
    append_event(tcr, case_dir, "EV_PUBLIC", ["C_PUBLIC", "C_PRIVATE"], ["SA"])

    out = tmp_path / "timeline"
    tcr.main(["export-timeline", str(cases_root), "--out-dir", str(out)])

    assert (out / "timeline.md").exists()
    cases = read_csv(out / "cases.csv")
    timeline = read_csv(out / "timeline.csv")
    corroborations = read_csv(out / "corroborations.csv")

    assert cases[0]["case_slug"] == "case_a"
    assert timeline[0]["event_id"] == "EV_PUBLIC"
    assert timeline[0]["claim_ids"] == "C_PUBLIC"
    assert timeline[0]["evidence_levels"] == "multi_source"
    assert [row["claim_id"] for row in corroborations] == ["C_PUBLIC"]
    assert corroborations[0]["source_count"] == "2"
    assert corroborations[0]["independent_source_count"] == "2"


def test_export_timeline_include_private_adds_internal_claims(tmp_path):
    tcr = load_tcr()
    case_dir = tmp_path / "case"
    tcr.main(["init-case", str(case_dir), "--title", "Single Case"])

    append_source(tcr, case_dir, "SA", "A", "Official Archive")
    append_claim(tcr, case_dir, "C_PRIVATE", ["SA"], public=False, status="disputed")
    append_event(tcr, case_dir, "EV_PRIVATE_REVIEW", ["C_PRIVATE"], ["SA"])

    out = tmp_path / "timeline"
    tcr.main(["export-timeline", str(case_dir), "--out-dir", str(out), "--include-private"])

    corroborations = read_csv(out / "corroborations.csv")
    timeline = read_csv(out / "timeline.csv")

    assert corroborations[0]["claim_id"] == "C_PRIVATE"
    assert corroborations[0]["evidence_level"] == "disputed"
    assert corroborations[0]["public_export"] == "False"
    assert timeline[0]["claim_ids"] == "C_PRIVATE"
