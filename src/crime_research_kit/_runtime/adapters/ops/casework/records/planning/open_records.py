"""Open-records request planning command."""

from __future__ import annotations

import argparse
import json

from crime_research_kit._runtime.core.casefile import case_path, ensure_case, log_action, now_utc, slugify, today, write_json

from crime_research_kit._runtime.adapters.ops.evidence.ledger.records import report_out_path


def plan_open_records(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    subject = args.subject.strip()
    agency = args.agency.strip()
    if not subject or not agency:
        raise SystemExit("--subject and --agency are required")
    requested_records = [item.strip() for item in (args.record or []) if item.strip()] or [
        f"public records concerning {subject}",
        "record indexes, logs, correspondence metadata, reports, policies, and responsive attachments where public",
    ]
    date_range = args.date_range or "date range to be narrowed before submission"
    jurisdiction = args.jurisdiction or "jurisdiction to confirm"
    law = args.law or "applicable FOIA/open-records law to confirm"
    report = {
        "generated_at": now_utc(),
        "case_dir": str(case_path(args.case_dir)),
        "subject": subject,
        "agency": agency,
        "jurisdiction": jurisdiction,
        "law": law,
        "date_range": date_range,
        "requested_records": requested_records,
        "privacy_exclusions": _privacy_exclusions(),
        "request_text": _request_text(agency, law, subject, jurisdiction, date_range, requested_records),
        "appeal_tracker": {
            "submitted_at": None,
            "tracking_number": None,
            "statutory_due_date": None,
            "response_status": "not_submitted",
            "appeal_due_date": None,
            "notes": "",
        },
        "policy": "This is a planning artifact. It does not create evidence claims or establish that records exist.",
    }
    default_name = f"staging/candidates/open_records_plan_{slugify(subject, max_len=32)}_{today()}.json"
    out = report_out_path(args.case_dir, getattr(args, "out", None), default_name)
    write_json(out, report)
    log_action(args.case_dir, "plan_open_records", {"subject": subject, "agency": agency, "jurisdiction": jurisdiction, "record_count": len(requested_records), "report": str(out)})
    print(json.dumps({"subject": subject, "agency": agency, "record_count": len(requested_records), "report": str(out)}, indent=2, ensure_ascii=False))


def _privacy_exclusions() -> list[str]:
    return [
        "home addresses, personal phone/email, financial identifiers, medical details, and private-person contact details",
        "records about minors unless already central to a public-interest record and legally releasable",
        "non-responsive private material and privileged/exempt content",
    ]


def _request_text(agency: str, law: str, subject: str, jurisdiction: str, date_range: str, requested_records: list[str]) -> str:
    return "\n".join(
        [
            f"To: {agency}",
            "",
            f"Under {law}, I request public records concerning {subject}.",
            f"Jurisdiction/scope: {jurisdiction}.",
            f"Date range: {date_range}.",
            "",
            "Requested record categories:",
            *[f"- {record}" for record in requested_records],
            "",
            "Please provide records electronically where available. Please segregate and release non-exempt portions of responsive records.",
            "Please exclude or redact private-person contact details, medical details, financial identifiers, and information about minors unless legally required and clearly responsive.",
            "If fees are expected, please provide an estimate before processing.",
        ]
    )
