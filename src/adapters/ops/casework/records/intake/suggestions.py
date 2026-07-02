"""Local candidate suggestions from registered source text."""

from __future__ import annotations

import argparse
import re
from typing import Any

from core.casefile import case_path, ensure_case, stable_id, today, write_json

from ..workspace import load_sources

DATE_RE = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
    re.I,
)
CAP_PHRASE_RE = re.compile(r"\b(?:[A-Z][a-zA-Z'\-.]+(?:\s+|$)){2,5}")


def make_candidate_id(prefix: str, name: str, source_id: str) -> str:
    return stable_id(prefix, name, source_id, length=8)


def ner_suggest(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    selected = [source for source in load_sources(args.case_dir) if not args.source_id or source.get("source_id") == args.source_id]
    candidates: list[dict[str, Any]] = []
    for source in selected:
        text_rel = source.get("text_path")
        if not text_rel:
            continue
        path = cdir / text_rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        candidates.extend(_name_candidates(text, source["source_id"], args.limit))
        candidates.extend(_date_candidates(text, source["source_id"], args.limit))
    out = cdir / "staging" / "candidates" / f"ner_suggestions_{today()}.json"
    write_json(out, {"candidates": candidates})
    print(f"Wrote {len(candidates)} candidates: {out}")


def _name_candidates(text: str, source_id: str, limit: int) -> list[dict[str, Any]]:
    rows = []
    names = sorted(
        {
            re.sub(r"\s+", " ", match.group(0)).strip()
            for match in CAP_PHRASE_RE.finditer(text)
            if len(match.group(0).strip()) >= 5
        }
    )
    for name in names[:limit]:
        if name.lower() in {"new york", "los angeles", "united states", "associated press"}:
            continue
        rows.append(_candidate("N", name, "unknown_named_entity", source_id))
    return rows


def _date_candidates(text: str, source_id: str, limit: int) -> list[dict[str, Any]]:
    return [_candidate("D", date, "date_or_time_expression", source_id) for date in sorted(set(DATE_RE.findall(text)))[:limit]]


def _candidate(prefix: str, name: str, candidate_type: str, source_id: str) -> dict[str, Any]:
    return {
        "candidate_id": make_candidate_id(prefix, name, source_id),
        "name": name,
        "candidate_type": candidate_type,
        "source_id": source_id,
        "status": "needs_human_or_agent_review",
    }
