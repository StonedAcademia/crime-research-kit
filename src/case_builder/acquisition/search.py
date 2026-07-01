"""Local SearXNG-backed source discovery."""

from __future__ import annotations

import datetime as dt
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from ..casefile import case_path, ensure_case, log_action, slugify


def discover_sources(
    case_dir: str | Path,
    *,
    query: str,
    searxng_url: str = "http://localhost:8080",
    limit: int = 10,
    out: str | None = None,
) -> dict[str, Any]:
    """Search a local SearXNG instance and write a lead-only candidate report."""
    ensure_case(case_dir)
    base = searxng_url.rstrip("/")
    params = urllib.parse.urlencode({"q": query, "format": "json", "language": "en"})
    request = urllib.request.Request(
        f"{base}/search?{params}",
        headers={"User-Agent": "truecrime-research-kit/0.1 local-source-discovery"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - user-configured local search
        payload = json.loads(response.read().decode("utf-8"))

    candidates = []
    for result in payload.get("results", [])[:limit]:
        candidates.append(
            {
                "title": result.get("title") or result.get("url"),
                "url": result.get("url"),
                "content": result.get("content") or "",
                "engine": result.get("engine"),
                "score": result.get("score"),
                "lead_only": True,
            }
        )
    report = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "query": query,
        "provider": "searxng",
        "provider_url": base,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "notes": "Discovery candidates are leads only. Register and preserve sources before extraction.",
    }
    output = Path(out) if out else case_path(case_dir) / "staging" / "candidates" / f"source_discovery_{slugify(query)}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log_action(case_dir, "discover_sources", {"query": query, "provider": "searxng", "report": str(output)})
    return {"report": str(output), "candidate_count": len(candidates)}
