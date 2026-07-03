"""Research brief writer for name-list linking runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crime_research_kit._runtime.core.casefile import case_path, slugify, today


def write_name_link_research_brief(
    case_dir: str | Path,
    *,
    entries: list[dict[str, Any]],
    resolved: list[dict[str, Any]],
    events: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    source_texts: dict[str, str],
    counts: dict[str, int],
) -> Path:
    cdir = case_path(case_dir)
    case_meta = json.loads((cdir / "case.json").read_text(encoding="utf-8"))
    case_title = case_meta.get("title", cdir.name)
    out = cdir / "notes" / f"name_link_research_{today()}_{slugify('_'.join(e['primary'] for e in entries), 40)}.md"
    source_titles = {str(source.get("source_id")): source.get("title", "") for source in sources}
    target_events = [event.get("title", "") for event in events if event.get("title")][:8]
    content = [
        f"# Name-link research brief: {case_title}",
        "",
        "## Purpose",
        "",
        "Use this brief to extend the source record for the listed names. The existing `link-names` pass writes only private, unverified co-mention links unless a reviewed extraction supplies stronger source-stated relationship language.",
        "",
        "## Current run",
        "",
        _table(["Metric", "Count"], [[key, str(value)] for key, value in sorted(counts.items())]),
        "",
        "## Names",
        "",
        _table(["Input", "Entity", "Matched sources", "Origin"], _name_rows(resolved)),
        "",
        "## Suggested search queries",
        "",
    ]
    for entry in entries:
        content.extend(_query_lines(entry["primary"], case_title, target_events))
    content.extend(
        [
            "## Source gaps",
            "",
            _table(["Name", "Gap"], _gap_rows(resolved)),
            "",
            "## Existing source text matches",
            "",
            _table(["Source", "Title", "Text available"], [[sid, source_titles.get(sid, ""), "yes"] for sid in sorted(source_texts)] or [["None", "", "no"]]),
            "",
            "## Agent-assisted web workflow",
            "",
            "1. Search the query list above using only public-interest, publicly available sources.",
            "2. Prefer official records, local reporting, strong investigative reporting, transcripts, and direct archives.",
            "3. Ingest or register each source before extracting facts.",
            "4. Fill extraction packets with source-stated entities, events, claims, relationships, and event links only.",
            "5. Re-run `link-names` after new sources are imported.",
            "",
            "## Safety notes",
            "",
            "- Co-mention is not evidence of guilt, membership, motive, or participation.",
            "- Keep living private people, minors, and weak allegations out of public exports.",
            "- Upgrade relation types only when a cited source explicitly supports the wording.",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(content) + "\n", encoding="utf-8")
    return out


def _name_rows(resolved: list[dict[str, Any]]) -> list[list[str]]:
    return [
        [item["entry"]["primary"], item["entity"].get("entity_id", ""), _flatten(sorted(item.get("source_ids", []))), item["entry"].get("origin", "")]
        for item in resolved
    ]


def _gap_rows(resolved: list[dict[str, Any]]) -> list[list[str]]:
    rows = [[item["entry"]["primary"], "No ingested source text currently mentions this name."] for item in resolved if not item.get("source_ids")]
    return rows or [["None", "All names matched at least one ingested source text or existing entity record."]]


def _query_lines(primary: str, case_title: str, event_titles: list[str]) -> list[str]:
    queries = [f'"{primary}" "{case_title}"', f'"{primary}" interview testimony affidavit', f'"{primary}" correction retraction disputed misidentified']
    queries.extend(f'"{primary}" "{event_title}"' for event_title in event_titles[:3])
    return [f"### {primary}", "", *(f"- `{query}`" for query in queries), ""]


def _table(headers: list[str], rows: list[list[str]]) -> str:
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |", *("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |" for row in rows)])


def _flatten(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ";".join(str(item) for item in value)
    return str(value)
