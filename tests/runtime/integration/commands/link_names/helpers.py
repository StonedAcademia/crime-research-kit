import importlib.util

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
    tcr.append_jsonl(
        tcr.record_path(case_dir, "sources"),
        {
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
        },
    )


def append_event(tcr, case_dir, event_id, source_ids, entity_ids=None):
    tcr.append_jsonl(
        tcr.record_path(case_dir, "events"),
        {
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
        },
    )


def assert_unique_ids(rows, id_field):
    values = [row[id_field] for row in rows]
    assert len(values) == len(set(values))
