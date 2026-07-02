"""Narrative-readiness review command."""

from __future__ import annotations

import argparse
import json
from typing import Any, Iterable

from core.casefile import case_path, ensure_case, log_action, now_utc, read_jsonl, record_path, write_json

from adapters.ops.casework.records.names.matching import clean_id_list
from adapters.ops.evidence.shared.records import public_rows, report_out_path, source_independence_key


def add_review_issue(
    issues: list[dict[str, Any]],
    *,
    record_type: str,
    record_id_value: str,
    issue_type: str,
    severity: str,
    message: str,
    field: str = "",
    value: Any = "",
) -> None:
    issues.append(
        {
            "record_type": record_type,
            "record_id": record_id_value,
            "issue_type": issue_type,
            "severity": severity,
            "field": field,
            "message": message,
            "value": str(value)[:280],
        }
    )


def review_narrative_readiness(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    sources = read_jsonl(record_path(args.case_dir, "sources"))
    claims = read_jsonl(record_path(args.case_dir, "claims"))
    events = read_jsonl(record_path(args.case_dir, "events"))
    relationships = read_jsonl(record_path(args.case_dir, "relationships"))
    source_by_id = {str(source.get("source_id")): source for source in sources if source.get("source_id")}
    if not getattr(args, "include_private", False):
        claims = public_rows(claims)
        events = public_rows(events)
        relationships = public_rows(relationships)
    issues: list[dict[str, Any]] = []
    _claim_issues(issues, claims, source_by_id, args.min_independent_sources, args.require_spans)
    _event_issues(issues, events, args.require_spans)
    _relationship_issues(issues, relationships)
    summary, severity_summary = _summaries(issues)
    report = {
        "generated_at": now_utc(),
        "case_dir": str(case_path(args.case_dir)),
        "include_private": getattr(args, "include_private", False),
        "min_independent_sources": args.min_independent_sources,
        "require_spans": args.require_spans,
        "issue_count": len(issues),
        "summary": summary,
        "severity_summary": severity_summary,
        "issues": issues,
        "policy": "Narrative readiness is advisory. Resolve blocker issues before public script, report, or artifact use.",
    }
    out = report_out_path(args.case_dir, getattr(args, "out", None), "exports/narrative_readiness_review.json")
    write_json(out, report)
    log_action(args.case_dir, "review_narrative_readiness", {"issue_count": len(issues), "summary": summary, "severity_summary": severity_summary, "report": str(out), "include_private": getattr(args, "include_private", False)})
    print(json.dumps({"issue_count": len(issues), "summary": summary, "severity_summary": severity_summary, "report": str(out)}, indent=2, ensure_ascii=False))
    if getattr(args, "fail_on_blockers", False) and severity_summary.get("blocker", 0):
        raise SystemExit(1)


def _claim_issues(issues: list[dict[str, Any]], claims: list[dict[str, Any]], source_by_id: dict[str, dict[str, Any]], min_sources: int, require_spans: bool) -> None:
    for claim in claims:
        claim_id = str(claim.get("claim_id", ""))
        source_ids = clean_id_list(claim.get("source_ids"))
        source_rows, missing_sources = _source_rows_for_ids(source_by_id, source_ids)
        status = str(claim.get("status", "")).casefold()
        assertion_type = str(claim.get("assertion_type", "")).casefold()
        privacy_review = str(claim.get("privacy_review", "clear") or "clear").casefold()
        independent_count = len({source_independence_key(source) for source in source_rows})
        if not source_ids:
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="missing_sources", severity="blocker", message="Narrative claim has no source_ids.")
        if missing_sources:
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="missing_source_records", severity="blocker", message="Narrative claim references missing source rows.", field="source_ids", value=";".join(missing_sources))
        if privacy_review != "clear":
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="privacy_not_clear", severity="blocker", message="Claim privacy review is not clear.", field="privacy_review", value=privacy_review)
        if status in {"unverified", "disputed", "false_or_retracted", "excluded_from_public_script"}:
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="needs_caveat_or_exclusion", severity="warning", message="Claim status requires caveat or exclusion from narrative.", field="status", value=status)
        if assertion_type == "lead_only":
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="lead_only_claim", severity="blocker", message="Lead-only claims are not narrative-ready.", field="assertion_type", value=assertion_type)
        if assertion_type == "allegation" and independent_count < min_sources:
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="weak_allegation_support", severity="blocker", message="Allegation lacks the configured independent source count.", field="source_ids", value=";".join(source_ids))
        if status == "corroborated" and independent_count < min_sources:
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="corroboration_independence_gap", severity="warning", message="Claim is marked corroborated but does not meet the configured independent source count.", field="source_ids", value=";".join(source_ids))
        if require_spans and not clean_id_list(claim.get("source_span_ids")):
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="missing_source_spans", severity="warning", message="Claim has no precise source_span_ids.")


def _event_issues(issues: list[dict[str, Any]], events: list[dict[str, Any]], require_spans: bool) -> None:
    for event in events:
        event_id = str(event.get("event_id", ""))
        if not clean_id_list(event.get("source_ids")):
            add_review_issue(issues, record_type="events", record_id_value=event_id, issue_type="missing_sources", severity="warning", message="Narrative event has no source_ids.")
        if require_spans and not clean_id_list(event.get("source_span_ids")):
            add_review_issue(issues, record_type="events", record_id_value=event_id, issue_type="missing_source_spans", severity="info", message="Event has no precise source_span_ids.")


def _relationship_issues(issues: list[dict[str, Any]], relationships: list[dict[str, Any]]) -> None:
    for rel in relationships:
        rel_id = str(rel.get("rel_id", ""))
        relation_type = str(rel.get("relation_type", ""))
        if relation_type in {"co_mentioned_with", "possibly_same_as"} and rel.get("public_export", True) is not False:
            add_review_issue(issues, record_type="relationships", record_id_value=rel_id, issue_type="lead_relationship_public", severity="blocker", message="Lead-only relationship is public-exportable.", field="relation_type", value=relation_type)
        if not clean_id_list(rel.get("source_ids")):
            add_review_issue(issues, record_type="relationships", record_id_value=rel_id, issue_type="missing_sources", severity="warning", message="Narrative relationship has no source_ids.")


def _source_rows_for_ids(source_by_id: dict[str, dict[str, Any]], source_ids: Iterable[str]) -> tuple[list[dict[str, Any]], list[str]]:
    rows, missing = [], []
    for source_id in source_ids:
        row = source_by_id.get(str(source_id))
        if row:
            rows.append(row)
        else:
            missing.append(str(source_id))
    return rows, missing


def _summaries(issues: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, int]]:
    summary: dict[str, int] = {}
    severity_summary: dict[str, int] = {}
    for issue in issues:
        issue_type = str(issue.get("issue_type", "unknown_issue"))
        severity = str(issue.get("severity", "blocker"))
        summary[issue_type] = summary.get(issue_type, 0) + 1
        severity_summary[severity] = severity_summary.get(severity, 0) + 1
    return summary, severity_summary
