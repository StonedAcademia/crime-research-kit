from __future__ import annotations

import os
import uuid
from pathlib import Path

from tests import helpers


def test_huggingface_qdrant_retrieval_round_trip(populated_mkultra_case: Path, crkit_runner):
    helpers.requires_extra("qdrant_client")
    from qdrant_client import QdrantClient

    base = helpers.live_service(os.environ.get("CRK_QDRANT_URL"), "/readyz")
    collection = f"crk_mkultra_live_{uuid.uuid4().hex[:12]}"
    client = QdrantClient(url=base)
    embed_model = os.environ.get("CRK_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
    try:
        indexed = crkit_runner(
            "index-case",
            str(populated_mkultra_case),
            "--qdrant-url",
            base,
            "--collection",
            collection,
            "--embed-model",
            embed_model,
        )
        assert indexed["collection"] == collection
        assert indexed["document_count"] > 0

        result = crkit_runner(
            "query-case",
            str(populated_mkultra_case),
            "What does the National Security Archive source say about CIA behavior control experiments?",
            "--qdrant-url",
            base,
            "--collection",
            collection,
            "--embed-model",
            embed_model,
            "--top-k",
            "3",
        )
        assert result["results"], "expected at least one retrieved evidence chunk"
        assert any(
            row.get("metadata", {}).get("source_id") or row.get("metadata", {}).get("source_ids")
            for row in result["results"]
        )
    finally:
        if client.collection_exists(collection):
            client.delete_collection(collection)
        client.close()
