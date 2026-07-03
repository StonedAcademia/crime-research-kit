import json
from pathlib import Path

import httpx

from crime_research_kit._runtime.adapters.io.acquisition import search
from crime_research_kit._runtime.adapters.io.acquisition.search import discover_sources

SEARX_PAYLOAD = {
    "results": [
        {
            "title": "Harbor Study Circle archive",
            "url": "https://example.org/archive/1",
            "content": "Lead snippet about the Harbor Study Circle.",
            "engine": "duckduckgo",
            "score": 1.0,
        }
    ]
}


def test_discover_sources_writes_lead_only_report(monkeypatch, synthetic_case_copy: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["format"] == "json"
        return httpx.Response(200, json=SEARX_PAYLOAD)

    monkeypatch.setattr(search, "_transport_for_tests", httpx.MockTransport(handler))

    result = discover_sources(synthetic_case_copy, query="Harbor Study Circle")

    report = json.loads(Path(result["report"]).read_text(encoding="utf-8"))
    assert result["candidate_count"] == 1
    assert report["provider"] == "searxng"
    candidate = report["candidates"][0]
    assert candidate["lead_only"] is True
    assert candidate["url"] == "https://example.org/archive/1"
    # Safety contract: discovery creates leads only — no evidence, no records mutated.
    assert "claims" not in report
    assert report["notes"].startswith("Discovery candidates are leads only")
