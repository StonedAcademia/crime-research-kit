import pytest

from tests.integration.crk_improvements.helpers import load_schema, validate_schema


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
        jsonschema.validate(instance=invalid_relationship, schema=load_schema("relationship.schema.json"))
