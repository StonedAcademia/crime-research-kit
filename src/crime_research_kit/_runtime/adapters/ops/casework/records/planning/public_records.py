"""Public-record lane planning command."""

from __future__ import annotations

import argparse
import json
from typing import Any

from crime_research_kit._runtime.core.casefile import case_path, ensure_case, log_action, now_utc, slugify, today, write_json
from crime_research_kit._runtime.core.lanes.registry import fallback_public_record_lanes, lane_records

from crime_research_kit._runtime.adapters.ops.evidence.ledger.records import report_out_path

PUBLIC_RECORD_LANES = {
    lane: {
        "skill": row["skill"],
        "triggers": row["triggers"],
        "source_types": row["source_types"],
        "template": row["template"],
        "notes": row["notes"],
    }
    for lane, row in lane_records(public_record_plan=True).items()
}
FALLBACK_PUBLIC_RECORD_LANES = fallback_public_record_lanes()


def infer_public_record_lanes(subject: str, requested_lanes: list[str]) -> list[str]:
    if requested_lanes:
        return sorted(dict.fromkeys(requested_lanes))
    text = subject.casefold()
    matches = [
        lane
        for lane, config in PUBLIC_RECORD_LANES.items()
        if any(trigger in text for trigger in config["triggers"])
    ]
    if matches:
        return sorted(dict.fromkeys(matches))
    return list(FALLBACK_PUBLIC_RECORD_LANES)


def public_record_lane_plan(lane: str, subject: str) -> dict[str, Any]:
    config = PUBLIC_RECORD_LANES[lane]
    return {
        "lane": lane,
        "skill": config["skill"],
        "template": config["template"],
        "source_types": config["source_types"],
        "notes": config["notes"],
        "suggested_queries": [f'"{subject}" {term}' for term in config["triggers"][:5]],
        "recommended_next_commands": [
            "add-source or ingest-url each public source before extraction",
            f"draft-extraction --template {config['template']} for lane-specific packets",
            "validate after imports",
        ],
    }


def plan_public_records(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    subject = args.subject.strip()
    if not subject:
        raise SystemExit("--subject is required")
    lanes = infer_public_record_lanes(subject, args.lane or [])
    report = {
        "generated_at": now_utc(),
        "case_dir": str(case_path(args.case_dir)),
        "subject": subject,
        "research_question": args.question or "",
        "lanes": [public_record_lane_plan(lane, subject) for lane in lanes],
        "policy": (
            "This source plan is a lead map. It does not create evidence, infer misconduct, "
            "or make identity/relationship claims."
        ),
    }
    default_name = f"staging/candidates/public_records_plan_{slugify(subject, max_len=32)}_{today()}.json"
    out = report_out_path(args.case_dir, getattr(args, "out", None), default_name)
    write_json(out, report)
    log_action(args.case_dir, "plan_public_records", {"subject": subject, "lanes": lanes, "report": str(out)})
    print(json.dumps({"lane_count": len(lanes), "lanes": lanes, "report": str(out)}, indent=2, ensure_ascii=False))
