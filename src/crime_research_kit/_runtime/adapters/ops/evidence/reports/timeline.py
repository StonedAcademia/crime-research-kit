"""Cross-case timeline and corroboration export command."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from crime_research_kit._runtime.core.casefile import read_jsonl, record_path

from crime_research_kit._runtime.adapters.ops.evidence.public_gate import enforce_public_output_gate
from crime_research_kit._runtime.adapters.ops.evidence.ledger.markdown import md_table
from crime_research_kit._runtime.adapters.ops.evidence.ledger.records import discover_cases, flatten, public_rows, source_independence_key, write_csv
from crime_research_kit._runtime.adapters.ops.evidence.ledger.scoring import date_sort_key, evidence_level, grade_summary
from crime_research_kit._runtime.adapters.ops.evidence.reports.common import reject_legacy_export_dir


def export_timeline(args: argparse.Namespace) -> None:
    enforce_public_output_gate(args.cases_root, "export-timeline", args.include_private)
    case_dirs = discover_cases(args.cases_root)
    include_private = args.include_private
    out = Path(args.out_dir).expanduser().resolve() if args.out_dir else _default_timeline_dir(args.cases_root, case_dirs)
    reject_legacy_export_dir(out)
    out.mkdir(parents=True, exist_ok=True)

    case_rows: list[dict[str, Any]] = []
    timeline_rows: list[dict[str, Any]] = []
    claim_rows: list[dict[str, Any]] = []

    for cdir in case_dirs:
        case_meta = json.loads((cdir / "case.json").read_text(encoding="utf-8"))
        case_slug = cdir.name
        case_id = case_meta.get("case_id", case_slug)
        case_title = case_meta.get("title", case_slug)
        sources = public_rows(read_jsonl(record_path(cdir, "sources")), include_private)
        claims = public_rows(read_jsonl(record_path(cdir, "claims")), include_private)
        events = public_rows(read_jsonl(record_path(cdir, "events")), include_private)
        relationships = public_rows(read_jsonl(record_path(cdir, "relationships")), include_private)
        source_by_id = {src.get("source_id"): src for src in sources}
        claim_by_id = {claim.get("claim_id"): claim for claim in claims}
        case_rows.append(
            {
                "case_slug": case_slug,
                "case_id": case_id,
                "case_title": case_title,
                "event_count": len(events),
                "claim_count": len(claims),
                "relationship_count": len(relationships),
                "source_count": len(sources),
                "include_private": include_private,
            }
        )
        _append_claim_rows(claim_rows, case_slug, case_id, case_title, claims, events, source_by_id)
        _append_timeline_rows(timeline_rows, case_slug, case_id, case_title, events, claim_by_id, source_by_id)

    timeline_rows.sort(key=lambda row: (date_sort_key(row.get("start_date")), row.get("case_slug", ""), row.get("event_id", "")))
    claim_rows.sort(key=lambda row: (row.get("case_slug", ""), row.get("status", ""), row.get("claim_id", "")))
    _write_csvs(out, case_rows, timeline_rows, claim_rows)
    _write_markdown(out, include_private, case_rows, timeline_rows, claim_rows)
    print(f"Exported cross-case timeline to {out}")


def _append_claim_rows(
    claim_rows: list[dict[str, Any]],
    case_slug: str,
    case_id: str,
    case_title: str,
    claims: list[dict[str, Any]],
    events: list[dict[str, Any]],
    source_by_id: dict[Any, dict[str, Any]],
) -> None:
    for claim in claims:
        source_ids = [sid for sid in claim.get("source_ids", []) if sid in source_by_id]
        source_rows = [source_by_id[sid] for sid in source_ids]
        independent_count = len({source_independence_key(src) for src in source_rows})
        related_events = [event.get("event_id", "") for event in events if claim.get("claim_id") in (event.get("claim_ids") or [])]
        claim_rows.append(
            {
                "case_slug": case_slug,
                "case_id": case_id,
                "case_title": case_title,
                "claim_id": claim.get("claim_id", ""),
                "claim": claim.get("claim", ""),
                "claim_type": claim.get("claim_type", ""),
                "status": claim.get("status", ""),
                "confidence": claim.get("confidence", ""),
                "privacy_review": claim.get("privacy_review", ""),
                "public_export": claim.get("public_export", True),
                "evidence_level": evidence_level(claim, source_rows),
                "source_count": len(source_rows),
                "independent_source_count": independent_count,
                "source_grades": grade_summary(source_rows),
                "source_ids": source_ids,
                "source_titles": [src.get("title", "") for src in source_rows],
                "event_ids": related_events,
            }
        )


def _append_timeline_rows(
    timeline_rows: list[dict[str, Any]],
    case_slug: str,
    case_id: str,
    case_title: str,
    events: list[dict[str, Any]],
    claim_by_id: dict[Any, dict[str, Any]],
    source_by_id: dict[Any, dict[str, Any]],
) -> None:
    for event in events:
        event_claims = [claim_by_id[claim_id] for claim_id in event.get("claim_ids", []) if claim_id in claim_by_id]
        source_ids = set(event.get("source_ids", []))
        for claim in event_claims:
            source_ids.update(claim.get("source_ids", []))
        source_rows = [source_by_id[sid] for sid in sorted(source_ids) if sid in source_by_id]
        claim_levels = [evidence_level(claim, [source_by_id[sid] for sid in claim.get("source_ids", []) if sid in source_by_id]) for claim in event_claims]
        timeline_rows.append(
            {
                "case_slug": case_slug,
                "case_id": case_id,
                "case_title": case_title,
                "event_id": event.get("event_id", ""),
                "start_date": event.get("start_date", ""),
                "end_date": event.get("end_date", ""),
                "date_precision": event.get("date_precision", ""),
                "event_type": event.get("event_type", ""),
                "title": event.get("title", ""),
                "status": event.get("status", ""),
                "confidence": event.get("confidence", ""),
                "public_export": event.get("public_export", True),
                "claim_count": len(event_claims),
                "claim_ids": [claim.get("claim_id", "") for claim in event_claims],
                "claim_statuses": sorted({str(claim.get("status", "")) for claim in event_claims}),
                "evidence_levels": sorted(set(claim_levels)),
                "source_count": len(source_rows),
                "source_grades": grade_summary(source_rows),
                "source_ids": [src.get("source_id", "") for src in source_rows],
                "notes": event.get("notes", ""),
            }
        )


def _write_csvs(out: Path, case_rows: list[dict[str, Any]], timeline_rows: list[dict[str, Any]], claim_rows: list[dict[str, Any]]) -> None:
    write_csv(out / "cases.csv", case_rows, ["case_slug", "case_id", "case_title", "event_count", "claim_count", "relationship_count", "source_count", "include_private"])
    write_csv(out / "timeline.csv", timeline_rows, ["case_slug", "case_id", "case_title", "event_id", "start_date", "end_date", "date_precision", "event_type", "title", "status", "confidence", "public_export", "claim_count", "claim_ids", "claim_statuses", "evidence_levels", "source_count", "source_grades", "source_ids", "notes"])
    write_csv(out / "corroborations.csv", claim_rows, ["case_slug", "case_id", "case_title", "claim_id", "claim", "claim_type", "status", "confidence", "privacy_review", "public_export", "evidence_level", "source_count", "independent_source_count", "source_grades", "source_ids", "source_titles", "event_ids"])


def _write_markdown(
    out: Path,
    include_private: bool,
    case_rows: list[dict[str, Any]],
    timeline_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
) -> None:
    level_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for row in claim_rows:
        level = str(row.get("evidence_level", "unknown"))
        status = str(row.get("status", "unknown"))
        level_counts[level] = level_counts.get(level, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1
    content = [
        "# Cross-case timeline and corroboration index",
        "",
        f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        f"Scope: {'public and private/internal rows' if include_private else 'public-export rows only'}",
        "",
        "## Cases",
        "",
        md_table(["Case", "Events", "Claims", "Relationships", "Sources"], [[row["case_title"], row["event_count"], row["claim_count"], row["relationship_count"], row["source_count"]] for row in case_rows]),
        "",
        "## Corroboration Summary",
        "",
        md_table(["Evidence level", "Claims"], [[level, count] for level, count in sorted(level_counts.items())]),
        "",
        md_table(["Claim status", "Claims"], [[status, count] for status, count in sorted(status_counts.items())]),
        "",
        "## Timeline",
        "",
        md_table(["Date", "Case", "Event", "Status", "Evidence", "Sources", "Claims"], [[row.get("start_date", ""), row.get("case_title", ""), row.get("title", ""), row.get("status", ""), flatten(row.get("evidence_levels")), row.get("source_grades", ""), flatten(row.get("claim_ids"))] for row in timeline_rows]),
        "",
        "## Claim Corroborations",
        "",
        md_table(["Case", "Claim", "Status", "Evidence", "Sources", "Events", "Public"], [[row.get("case_title", ""), row.get("claim_id", ""), row.get("status", ""), row.get("evidence_level", ""), row.get("source_grades", ""), flatten(row.get("event_ids")), row.get("public_export", "")] for row in claim_rows]),
    ]
    (out / "timeline.md").write_text("\n".join(str(line) for line in content) + "\n", encoding="utf-8")


def _default_timeline_dir(cases_root: str | Path, case_dirs: list[Path]) -> Path:
    root = Path(cases_root).expanduser().resolve()
    if len(case_dirs) == 1 and (root / "case.json").exists():
        return case_dirs[0] / "exports" / "internal" / "timeline"
    return root.parent / "exports" / "internal" / "timeline"
