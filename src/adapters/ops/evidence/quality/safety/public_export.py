"""Public-export safety audit command."""

from __future__ import annotations

import argparse
import json
import re
from typing import Any, Iterable

from core.casefile import RECORD_FILES, case_path, ensure_case, log_action, now_utc, read_jsonl, record_path, write_json

from adapters.ops.casework.records.names.matching import clean_id_list
from adapters.ops.evidence.ledger.records import record_id, report_out_path, source_independence_key

PUBLIC_CONTACT_RE = re.compile(
    r"(?i)(?:\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b|\b\d{3}-\d{2}-\d{4}\b)"
)
ADDRESS_RE = re.compile(
    r"(?i)\b\d{1,6}\s+[A-Z0-9][A-Z0-9'.-]*(?:\s+[A-Z0-9][A-Z0-9'.-]*){0,5}\s+"
    r"(?:street|st\.?|avenue|ave\.?|road|rd\.?|drive|dr\.?|lane|ln\.?|boulevard|blvd\.?|court|ct\.?|place|pl\.?|way)\b"
)
CONTACT_FIELD_RE = re.compile(r"(?:^|_)(?:address|phone|telephone|email|contact|home_address|mailing_address)(?:$|_)", re.I)
ALLEGATION_RE = re.compile(
    r"\b(?:accus(?:e|ed|ation)|alleg(?:e|ed|ation)|abuse|assault|charged|criminal|"
    r"cult member|perpetrator|person of interest|suspect|rumou?r|unverified)\b",
    re.I,
)


def public_export_enabled(row: dict[str, Any]) -> bool:
    return row.get("public_export", True) is not False


def text_fields_for_public_scan(row: Any, prefix: str = "") -> list[tuple[str, str]]:
    skip = {"url", "archive_url", "raw_path", "text_path", "source_text_path", "source_metadata"}
    if isinstance(row, dict):
        values: list[tuple[str, str]] = []
        for key, value in row.items():
            if key not in skip:
                values.extend(text_fields_for_public_scan(value, f"{prefix}.{key}" if prefix else str(key)))
        return values
    if isinstance(row, list):
        values = []
        for idx, value in enumerate(row):
            values.extend(text_fields_for_public_scan(value, f"{prefix}[{idx}]"))
        return values
    return [] if row in (None, "") else [(prefix, str(row))]


def add_audit_issue(
    issues: list[dict[str, Any]],
    *,
    record_type: str,
    record_id_value: str,
    issue_type: str,
    message: str,
    field: str = "",
    value: str = "",
) -> None:
    issues.append({"record_type": record_type, "record_id": record_id_value, "issue_type": issue_type, "field": field, "message": message, "value": value[:240]})


def source_rows_for_ids(source_by_id: dict[str, dict[str, Any]], source_ids: Iterable[str]) -> tuple[list[dict[str, Any]], list[str]]:
    rows, missing = [], []
    for source_id in source_ids:
        source = source_by_id.get(str(source_id))
        if source:
            rows.append(source)
        else:
            missing.append(str(source_id))
    return rows, missing


def audit_claim_public_support(
    issues: list[dict[str, Any]],
    claim: dict[str, Any],
    claim_id: str,
    source_by_id: dict[str, dict[str, Any]],
) -> None:
    source_ids = clean_id_list(claim.get("source_ids"))
    if not source_ids:
        add_audit_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="unsupported_claim", message="Public claim has no source_ids.")
        return
    source_rows, missing = source_rows_for_ids(source_by_id, source_ids)
    if missing:
        add_audit_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="unsupported_claim", message="Public claim references source_ids that are not in records/sources.jsonl.", field="source_ids", value=";".join(missing))
    if not source_rows:
        return
    grades = {str(source.get("reliability_grade", "")).upper() for source in source_rows}
    text = " ".join(str(claim.get(field, "")) for field in ("claim", "claim_type", "status", "notes"))
    status = str(claim.get("status", "")).casefold()
    assertion_type = str(claim.get("assertion_type", "")).casefold()
    privacy_review = str(claim.get("privacy_review", "clear") or "clear").casefold()
    confidence = _confidence(claim.get("confidence"))
    independent_count = len({source_independence_key(source) for source in source_rows})
    if privacy_review != "clear":
        add_audit_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="privacy_review_not_clear", message="Public claim has not cleared privacy review.", field="privacy_review", value=privacy_review)
    if assertion_type == "lead_only":
        add_audit_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="lead_only_or_weak_allegation", message="Public claim is marked assertion_type=lead_only.", field="assertion_type", value=assertion_type)
    if status == "unverified" and (confidence is None or confidence < 0.5):
        add_audit_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="unsupported_claim", message="Public claim is unverified and low-confidence.", field="status", value=status)
    if grades and all(grade in {"", "D", "X"} for grade in grades):
        add_audit_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="weak_claim_sources", message="Public claim is supported only by lead-only or excluded source grades.", field="source_ids", value=";".join(source_ids))
    if _weak_allegation(assertion_type, text, status, confidence, independent_count):
        add_audit_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="lead_only_or_weak_allegation", message="Public allegation is lead-only, weakly supported, low-confidence, or lacks independent corroboration.", field="claim", value=str(claim.get("claim", "")))


def audit_public_export(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    sources = read_jsonl(record_path(args.case_dir, "sources"))
    source_by_id = {str(source.get("source_id")): source for source in sources if source.get("source_id")}
    issues: list[dict[str, Any]] = []
    for record_name in RECORD_FILES:
        if record_name == "research_actions":
            continue
        for idx, row in enumerate(read_jsonl(record_path(args.case_dir, record_name)), start=1):
            if public_export_enabled(row):
                _audit_row(issues, record_name, row, record_id(record_name, row, idx), source_by_id)
    summary: dict[str, int] = {}
    for issue in issues:
        key = str(issue["issue_type"])
        summary[key] = summary.get(key, 0) + 1
    report = {"generated_at": now_utc(), "case_dir": str(case_path(args.case_dir)), "issue_count": len(issues), "summary": summary, "issues": issues}
    out = report_out_path(args.case_dir, getattr(args, "out", None), "exports/public_export_audit.json")
    write_json(out, report)
    log_action(args.case_dir, "audit_public_export", {"issue_count": len(issues), "summary": summary, "report": str(out), "warn_only": getattr(args, "warn_only", False)})
    print(json.dumps({"issue_count": len(issues), "summary": summary, "report": str(out)}, indent=2, ensure_ascii=False))
    if issues and not getattr(args, "warn_only", False):
        raise SystemExit(1)


def _audit_row(issues: list[dict[str, Any]], record_name: str, row: dict[str, Any], rid: str, source_by_id: dict[str, dict[str, Any]]) -> None:
    privacy_review = str(row.get("privacy_review", "")).casefold()
    if privacy_review in {"needs_review", "redact", "exclude"}:
        add_audit_issue(issues, record_type=record_name, record_id_value=rid, issue_type="privacy_review_blocks_public_export", message="Public record has privacy_review that blocks or requires review before export.", field="privacy_review", value=str(row.get("privacy_review", "")))
    _scan_text(issues, record_name, row, rid)
    if record_name == "entities":
        _audit_entity(issues, row, rid)
    if record_name == "sources" and str(row.get("reliability_grade", "")).upper() in {"D", "X"}:
        add_audit_issue(issues, record_type=record_name, record_id_value=rid, issue_type="lead_only_or_excluded_source_public", message="Public export includes a lead-only or excluded source grade.", field="reliability_grade", value=str(row.get("reliability_grade", "")).upper())
    if record_name == "claims":
        audit_claim_public_support(issues, row, rid, source_by_id)
    if record_name in {"events", "event_links", "relationships"} and not clean_id_list(row.get("source_ids")):
        add_audit_issue(issues, record_type=record_name, record_id_value=rid, issue_type="unsupported_public_record", message="Public record has no source_ids.", field="source_ids")


def _scan_text(issues: list[dict[str, Any]], record_name: str, row: dict[str, Any], rid: str) -> None:
    for field, text in text_fields_for_public_scan(row):
        if CONTACT_FIELD_RE.search(field):
            add_audit_issue(issues, record_type=record_name, record_id_value=rid, issue_type="address_or_contact_info", message="Public record contains an address/contact field.", field=field, value=text)
        elif PUBLIC_CONTACT_RE.search(text) or ADDRESS_RE.search(text):
            add_audit_issue(issues, record_type=record_name, record_id_value=rid, issue_type="address_or_contact_info", message="Public record text appears to contain address/contact information.", field=field, value=text)


def _audit_entity(issues: list[dict[str, Any]], row: dict[str, Any], rid: str) -> None:
    privacy = " ".join(str(row.get(field, "")) for field in ("privacy_level", "status", "notes")).casefold()
    roles = " ".join(str(item) for item in (row.get("role_tags") or [])).casefold()
    if "private_person" in privacy or privacy in {"private", "private person"} or "private_person" in roles:
        add_audit_issue(issues, record_type="entities", record_id_value=rid, issue_type="private_person_public", message="Public export includes an entity marked as a private person.", field="privacy_level", value=str(row.get("privacy_level", "")))
    if re.search(r"\b(?:minor|juvenile|child|underage)\b", privacy + " " + roles):
        add_audit_issue(issues, record_type="entities", record_id_value=rid, issue_type="minor_public", message="Public export includes an entity marked as or describing a minor.", field="privacy_level", value=str(row.get("privacy_level", "")))


def _confidence(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _weak_allegation(assertion_type: str, text: str, status: str, confidence: float | None, independent_count: int) -> bool:
    return (assertion_type == "allegation" or ALLEGATION_RE.search(text)) and (
        "lead" in status
        or status in {"unverified", "rumor", "unsupported", "single_source"}
        or (confidence is not None and confidence < 0.5)
        or independent_count < 2
    )
