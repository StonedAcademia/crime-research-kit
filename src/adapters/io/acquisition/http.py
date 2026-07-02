"""HTTP acquisition helpers for public-source capture."""

from __future__ import annotations

import urllib.request


DEFAULT_USER_AGENT = "truecrime-research-kit/0.1 (+public-interest research; contact: local-user)"


def fetch_url(url: str, timeout: int = 25) -> tuple[str, bytes, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-requested URL ingestion
        content_type = response.headers.get("Content-Type", "")
        return content_type, response.read(), dict(response.headers.items())
