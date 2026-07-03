import os

import pytest

from tests import helpers


def _mock_embed():
    from llama_index.core.embeddings.mock_embed_model import MockEmbedding

    return MockEmbedding(embed_dim=16)


@pytest.fixture
def mock_embed():
    helpers.requires_extra("llama_index.core")
    return _mock_embed()


@pytest.fixture(params=["memory", "live"])
def qdrant_backend(request):
    helpers.requires_extra("qdrant_client")
    from qdrant_client import QdrantClient

    if request.param == "memory":
        client = QdrantClient(location=":memory:")
        yield client
        client.close()
        return
    base = helpers.live_service(os.environ.get("CRK_QDRANT_URL"), "/readyz")
    client = QdrantClient(url=base)
    yield client
    client.close()
