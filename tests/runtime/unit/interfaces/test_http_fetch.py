"""httpx-backed fetch_url contract and retry behavior."""

from __future__ import annotations

import httpx
import pytest

from adapters.io.acquisition.http import DEFAULT_USER_AGENT, fetch_url


def _transport(handler):
    return httpx.MockTransport(handler)


def test_fetch_url_contract(monkeypatch):
    def handler(request):
        assert request.headers["User-Agent"] == DEFAULT_USER_AGENT
        return httpx.Response(200, headers={"Content-Type": "text/html"}, content=b"<html>ok</html>")

    monkeypatch.setattr("adapters.io.acquisition.http._transport_for_tests", _transport(handler))
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

    monkeypatch.setattr("adapters.io.acquisition.http._transport_for_tests", _transport(handler))
    monkeypatch.setattr("adapters.io.acquisition.http._sleep", lambda seconds: None)
    _content_type, body, _headers = fetch_url("https://example.org/x")
    assert body == b"ok"
    assert calls["n"] == 3


def test_fetch_url_gives_up_after_three_attempts(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503, request=request)

    monkeypatch.setattr("adapters.io.acquisition.http._transport_for_tests", _transport(handler))
    monkeypatch.setattr("adapters.io.acquisition.http._sleep", lambda seconds: None)
    with pytest.raises(httpx.HTTPStatusError):
        fetch_url("https://example.org/x")
    assert calls["n"] == 3


def test_fetch_url_does_not_retry_4xx(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(404, request=request)

    monkeypatch.setattr("adapters.io.acquisition.http._transport_for_tests", _transport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        fetch_url("https://example.org/x")
    assert calls["n"] == 1
