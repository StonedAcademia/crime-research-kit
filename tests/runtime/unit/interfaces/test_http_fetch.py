"""httpx-backed fetch_url contract and retry behavior."""

from __future__ import annotations

import httpx
import pytest

from crime_research_kit._runtime.adapters.io.acquisition.http import (
    DEFAULT_USER_AGENT,
    fetch_url,
    fetch_url_or_archive,
)


def _transport(handler):
    return httpx.MockTransport(handler)


def test_fetch_url_contract(monkeypatch):
    def handler(request):
        assert request.headers["User-Agent"] == DEFAULT_USER_AGENT
        return httpx.Response(200, headers={"Content-Type": "text/html"}, content=b"<html>ok</html>")

    monkeypatch.setattr("crime_research_kit._runtime.adapters.io.acquisition.http._transport_for_tests", _transport(handler))
    content_type, body, headers = fetch_url("https://example.org/x")
    assert content_type.startswith("text/html")
    assert body == b"<html>ok</html>"
    assert headers["content-type"].startswith("text/html")


def test_fetch_url_retries_5xx_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(500, request=request)
        return httpx.Response(200, content=b"ok", request=request)

    monkeypatch.setattr("crime_research_kit._runtime.adapters.io.acquisition.http._transport_for_tests", _transport(handler))
    monkeypatch.setattr("crime_research_kit._runtime.adapters.io.acquisition.http._sleep", lambda seconds: None)
    _content_type, body, _headers = fetch_url("https://example.org/x")
    assert body == b"ok"
    assert calls["n"] == 3


def test_fetch_url_gives_up_after_three_attempts(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503, request=request)

    monkeypatch.setattr("crime_research_kit._runtime.adapters.io.acquisition.http._transport_for_tests", _transport(handler))
    monkeypatch.setattr("crime_research_kit._runtime.adapters.io.acquisition.http._sleep", lambda seconds: None)
    with pytest.raises(httpx.HTTPStatusError):
        fetch_url("https://example.org/x")
    assert calls["n"] == 3


def test_fetch_url_does_not_retry_4xx(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(404, request=request)

    monkeypatch.setattr("crime_research_kit._runtime.adapters.io.acquisition.http._transport_for_tests", _transport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        fetch_url("https://example.org/x")
    assert calls["n"] == 1


def test_fetch_url_or_archive_returns_original_on_success(monkeypatch):
    def handler(request):
        return httpx.Response(200, headers={"Content-Type": "text/html"}, content=b"live", request=request)

    monkeypatch.setattr("crime_research_kit._runtime.adapters.io.acquisition.http._transport_for_tests", _transport(handler))
    _ct, body, _headers, served = fetch_url_or_archive("https://law.example.com/case")
    assert body == b"live"
    assert served == "https://law.example.com/case"


def test_fetch_url_or_archive_falls_back_to_wayback_on_403(monkeypatch):
    def handler(request):
        if "web.archive.org" in request.url.host:
            return httpx.Response(200, headers={"Content-Type": "text/html"}, content=b"archived", request=request)
        return httpx.Response(403, request=request)

    monkeypatch.setattr("crime_research_kit._runtime.adapters.io.acquisition.http._transport_for_tests", _transport(handler))
    _ct, body, _headers, served = fetch_url_or_archive("https://law.example.com/case")
    assert body == b"archived"
    assert served == "https://web.archive.org/web/2/https://law.example.com/case"


def test_fetch_url_or_archive_reraises_non_antibot_status(monkeypatch):
    def handler(request):
        assert "web.archive.org" not in request.url.host, "must not fall back on a plain 404"
        return httpx.Response(404, request=request)

    monkeypatch.setattr("crime_research_kit._runtime.adapters.io.acquisition.http._transport_for_tests", _transport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        fetch_url_or_archive("https://example.org/missing")
