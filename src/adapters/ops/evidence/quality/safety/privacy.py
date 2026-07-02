"""Privacy-redaction audit command."""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

from core.casefile import RECORD_FILES, case_path, ensure_case, log_action, now_utc, read_jsonl, record_path, write_json

from adapters.ops.evidence.quality.safety.public_export import (
    ADDRESS_RE,
    CONTACT_FIELD_RE,
    PUBLIC_CONTACT_RE,
    audit_claim_public_support,
    text_fields_for_public_scan,
)
from adapters.ops.evidence.quality.safety.readiness import add_review_issue
from adapters.ops.evidence.shared.records import record_id, report_out_path


def audit_privacy_redactions(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    sources = read_jsonl(record_path(args.case_dir, "sources"))
    source_by_id = {str(source.get("source_id")): source for source in sources if source.get("source_id")}
    issues: list[dict[str, Any]] = []

    for record_name in RECORD_FILES:
        if record_name == "research_actions":
            continue
        for idx, row in enumerate(read_jsonl(record_path(args.case_dir, record_name)), start=1):
            if row.get("public_export", True) is False and not getattr(args, "include_private", False):
                continue
            _audit_record(issues, record_name, row, record_id(record_name, row, idx), source_by_id)

    _audit_redactions(issues, args)
    summary, severity_summary = _summaries(issues)
    report = {
        "generated_at": now_utc(),
        "case_dir": str(cdir),
        "include_private": getattr(args, "include_private", False),
        "issue_count": len(issues),
        "summary": summary,
        "severity_summary": severity_summary,
        "issues": issues,
    }
    out = report_out_path(args.case_dir, getattr(args, "out", None), "exports/privacy_redaction_audit.json")
    write_json(out, report)
    log_action(
        args.case_dir,
        "audit_privacy_redactions",
        {
            "issue_count": len(issues),
            "summary": summary,
            "severity_summary": severity_summary,
            "report": str(out),
            "include_private": getattr(args, "include_private", False),
        },
    )
    print(json.dumps({"issue_count": len(issues), "summary": summary, "severity_summary": severity_summary, "report": str(out)}, indent=2, ensure_ascii=False))
    if issues and not getattr(args, "warn_only", False):
        raise SystemExit(1)


def _audit_record(
    issues: list[dict[str, Any]],
    record_name: str,
    row: dict[str, Any],
    rid: str,
    source_by_id: dict[str, dict[str, Any]],
) -> None:
    privacy_review = str(row.get("privacy_review", "")).casefold()
    if row.get("public_export", True) is not False and privacy_review in {"needs_review", "redact", "exclude"}:
        add_review_issue(issues, record_type=record_name, record_id_value=rid, issue_type="public_record_privacy_review_open", severity="blocker", message="Public record has privacy_review that requires review, redaction, or exclusion.", field="privacy_review", value=privacy_review)
    _scan_text(issues, record_name, row, rid)
    if record_name == "entities":
        _audit_entity(issues, row, rid)
    if record_name == "claims":
        audit_claim_public_support(issues, row, rid, source_by_id)


def _scan_text(issues: list[dict[str, Any]], record_name: str, row: dict[str, Any], rid: str) -> None:
    for field, text in text_fields_for_public_scan(row):
        if CONTACT_FIELD_RE.search(field):
            add_review_issue(issues, record_type=record_name, record_id_value=rid, issue_type="contact_field_present", severity="blocker", message="Record has an address/contact-style field.", field=field, value=text)
        elif PUBLIC_CONTACT_RE.search(text) or ADDRESS_RE.search(text):
            add_review_issue(issues, record_type=record_name, record_id_value=rid, issue_type="contact_or_address_pattern", severity="blocker", message="Record text appears to contain contact or address information.", field=field, value=text)


def _audit_entity(issues: list[dict[str, Any]], row: dict[str, Any], rid: str) -> None:
    privacy_text = " ".join(str(row.get(field, "")) for field in ("privacy_level", "status", "notes")).casefold()
    roles_text = " ".join(str(item) for item in (row.get("role_tags") or [])).casefold()
    if row.get("public_export", True) is not False and ("private_person" in privacy_text or "private_person" in roles_text):
        add_review_issue(issues, record_type="entities", record_id_value=rid, issue_type="private_person_public", severity="blocker", message="Private-person entity is public-exportable.", field="privacy_level", value=row.get("privacy_level", ""))
    if row.get("public_export", True) is not False and re.search(r"\b(?:minor|juvenile|child|underage)\b", privacy_text + " " + roles_text):
        add_review_issue(issues, record_type="entities", record_id_value=rid, issue_type="minor_public", severity="blocker", message="Minor-related entity is public-exportable.", field="privacy_level", value=row.get("privacy_level", ""))


def _audit_redactions(issues: list[dict[str, Any]], args: argparse.Namespace) -> None:
    redactions = read_jsonl(record_path(args.case_dir, "redactions"))
    if not redactions and args.require_redaction_log:
        add_review_issue(issues, record_type="redactions", record_id_value="redactions", issue_type="missing_redaction_log", severity="warning", message="No redaction rows exist for this case.")
    for idx, row in enumerate(redactions, start=1):
        rid = record_id("redactions", row, idx)
        status = str(row.get("status", row.get("review_status", ""))).casefold()
        if status in {"open", "pending", "needs_review", "unresolved"}:
            add_review_issue(issues, record_type="redactions", record_id_value=rid, issue_type="open_redaction", severity="warning", message="Redaction row appears unresolved.", field="status", value=status)


def _summaries(issues: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, int]]:
    summary: dict[str, int] = {}
    severity_summary: dict[str, int] = {}
    for issue in issues:
        issue_type = str(issue.get("issue_type", "unknown_issue"))
        severity = str(issue.get("severity", "blocker"))
        summary[issue_type] = summary.get(issue_type, 0) + 1
        severity_summary[severity] = severity_summary.get(severity, 0) + 1
    return summary, severity_summary
