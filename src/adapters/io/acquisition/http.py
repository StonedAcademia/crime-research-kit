"""HTTP acquisition helpers for public-source capture."""

from __future__ import annotations

import time

import httpx


DEFAULT_USER_AGENT = "truecrime-research-kit/0.1 (+public-interest research; contact: local-user)"
_RETRY_ATTEMPTS = 3
_transport_for_tests: httpx.BaseTransport | None = None


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def fetch_url(url: str, timeout: int = 25) -> tuple[str, bytes, dict[str, str]]:
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    with httpx.Client(follow_redirects=True, timeout=timeout, transport=_transport_for_tests) as client:
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                response = client.get(url, headers=headers)
                if response.status_code >= 500 and attempt < _RETRY_ATTEMPTS - 1:
                    _sleep(0.5 * 2**attempt)
                    continue
                response.raise_for_status()
                return response.headers.get("Content-Type", ""), response.content, dict(response.headers)
            except (httpx.ConnectError, httpx.ConnectTimeout):
                if attempt < _RETRY_ATTEMPTS - 1:
                    _sleep(0.5 * 2**attempt)
                    continue
                raise
    raise RuntimeError("fetch_url exhausted retry attempts without a response")
