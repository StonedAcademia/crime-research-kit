import os

import httpx

from tests import helpers


def test_qdrant_ready():
    base = helpers.live_service(os.environ.get("CRK_QDRANT_URL"), "/readyz")
    assert httpx.get(base + "/readyz", timeout=5).status_code == 200


def test_searxng_search_json():
    base = helpers.live_service(os.environ.get("CRK_SEARXNG_URL"), "/healthz")
    response = httpx.get(base + "/search", params={"q": "crk", "format": "json"}, timeout=10)
    response.raise_for_status()
    assert "results" in response.json()


def test_ollama_tags():
    base = helpers.live_service(os.environ.get("OLLAMA_HOST"), "/api/tags")
    response = httpx.get(base + "/api/tags", timeout=10)
    response.raise_for_status()
    assert "models" in response.json()
