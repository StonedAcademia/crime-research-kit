"""HTTP acquisition helpers for public-source capture."""

from __future__ import annotations

import time

import httpx


DEFAULT_USER_AGENT = "truecrime-research-kit/0.1 (+public-interest research; contact: local-user)"
_RETRY_ATTEMPTS = 3
_transport_for_tests: httpx.BaseTransport | None = None


_ANTI_BOT_STATUSES = frozenset({401, 403, 429, 451})


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def fetch_url_or_archive(url: str, timeout: int = 25) -> tuple[str, bytes, dict[str, str], str]:
    """Fetch ``url``; on an anti-bot/blocked response, retry via the Internet Archive.

    Returns ``(content_type, raw, headers, served_url)`` where ``served_url`` is the URL
    that actually delivered the content — the Wayback Machine URL when the fallback fired,
    otherwise the original. Used by public-source capture so anti-bot pages (e.g. some
    court-opinion republishers) still yield an archived copy instead of failing outright.
    """
    try:
        content_type, raw, headers = fetch_url(url, timeout=timeout)
        return content_type, raw, headers, url
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status not in _ANTI_BOT_STATUSES:
            raise
        archive_url = f"https://web.archive.org/web/2/{url}"
        content_type, raw, headers = fetch_url(archive_url, timeout=timeout)
        return content_type, raw, headers, archive_url


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
