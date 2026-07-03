import json
from pathlib import Path

from crime_research_kit._runtime.adapters.io.retrieval import index_case, query_case

COLLECTION = "crk_test_retrieval"


def _reset(client):
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)


def test_index_then_query_round_trip(synthetic_case_copy: Path, qdrant_backend, mock_embed):
    _reset(qdrant_backend)

    indexed = index_case(
        synthetic_case_copy,
        collection=COLLECTION,
        client=qdrant_backend,
        embed=mock_embed,
    )
    assert indexed["document_count"] > 0
    assert indexed["collection"] == COLLECTION

    result = query_case(
        synthetic_case_copy,
        "Harbor Study Circle",
        collection=COLLECTION,
        client=qdrant_backend,
        embed=mock_embed,
        top_k=5,
    )
    assert result["results"], "expected at least one retrieved node"
    first = result["results"][0]
    assert "score" in first and "text" in first and "metadata" in first
    _reset(qdrant_backend)


def test_private_records_excluded_by_default(synthetic_case_copy: Path, qdrant_backend, mock_embed):
    claims = synthetic_case_copy / "records" / "claims.jsonl"
    claims.write_text(
        claims.read_text(encoding="utf-8")
        + json.dumps(
            {
                "claim_id": "CPRIV",
                "claim": "Private review-only marker phrase.",
                "status": "unverified",
                "confidence": 0.1,
                "source_ids": ["SDEMO0001"],
                "public_export": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _reset(qdrant_backend)
    public = index_case(synthetic_case_copy, collection=COLLECTION, client=qdrant_backend, embed=mock_embed)
    _reset(qdrant_backend)
    private = index_case(
        synthetic_case_copy, collection=COLLECTION, include_private=True, client=qdrant_backend, embed=mock_embed
    )
    assert private["document_count"] > public["document_count"]
    _reset(qdrant_backend)


def test_index_case_without_retrieval_extra_raises(monkeypatch, synthetic_case_copy: Path):
    import sys

    # Simulate the retrieval extra being absent.
    monkeypatch.setitem(sys.modules, "llama_index.core", None)
    import pytest

    with pytest.raises(RuntimeError, match="retrieval extra"):
        index_case(synthetic_case_copy, collection=COLLECTION)
