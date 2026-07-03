"""Public-output safety gate for export commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from crime_research_kit._runtime.adapters.ops.evidence.quality.contradictions import audit_contradictions
from crime_research_kit._runtime.adapters.ops.evidence.quality.safety.privacy import audit_privacy_redactions
from crime_research_kit._runtime.adapters.ops.evidence.quality.safety.public_export import audit_public_export
from crime_research_kit._runtime.adapters.ops.evidence.quality.safety.readiness import review_narrative_readiness
from crime_research_kit._runtime.adapters.ops.evidence.quality.safety.source_independence import source_independence
from crime_research_kit._runtime.adapters.ops.evidence.ledger.records import discover_cases


def collect_public_output_blockers(label: str, report_path: Path) -> list[str]:
    if not report_path.exists():
        return [f"{label}: missing audit report {report_path}"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    blockers: list[str] = []
    if label == "audit-public-export":
        for issue in report.get("issues", []):
            blockers.append(f"{label}: {issue.get('issue_type', 'issue')} {issue.get('record_id', '')}".strip())
    else:
        for issue in report.get("issues", []):
            if str(issue.get("severity", "blocker")) == "blocker":
                blockers.append(f"{label}: {issue.get('issue_type', 'issue')} {issue.get('record_id', '')}".strip())
        for flag in report.get("flags", []):
            if str(flag.get("severity", "")).casefold() == "blocker":
                blockers.append(f"{label}: {flag.get('flag_type', 'flag')} {flag.get('record_id', '')}".strip())
    return blockers


def enforce_public_output_gate(target: str | Path, command_name: str, include_private: bool = False) -> None:
    if include_private:
        print(f"{command_name}: internal export requested with --include-private; public-output gate skipped.")
        return
    blockers: list[str] = []
    for case_dir in discover_cases(target):
        audit_public_export(argparse.Namespace(case_dir=str(case_dir), out=None, warn_only=True))
        audit_privacy_redactions(argparse.Namespace(case_dir=str(case_dir), out=None, include_private=False, require_redaction_log=False, warn_only=True))
        audit_contradictions(argparse.Namespace(case_dir=str(case_dir), out=None, include_private=False, min_overlap=0.45, fail_on_flags=False))
        source_independence(argparse.Namespace(case_dir=str(case_dir), out=None, include_private=False, min_title_chars=16, fail_on_flags=False))
        review_narrative_readiness(argparse.Namespace(case_dir=str(case_dir), out=None, include_private=False, require_spans=False, min_independent_sources=2, fail_on_blockers=False))
        reports = {
            "audit-public-export": case_dir / "exports" / "public_export_audit.json",
            "audit-privacy-redactions": case_dir / "exports" / "privacy_redaction_audit.json",
            "audit-contradictions": case_dir / "exports" / "claim_contradiction_audit.json",
            "audit-source-independence": case_dir / "exports" / "source_independence_report.json",
            "review-narrative-readiness": case_dir / "exports" / "narrative_readiness_review.json",
        }
        for label, report_path in reports.items():
            blockers.extend(collect_public_output_blockers(label, report_path))
    if blockers:
        print(f"{command_name}: public export blocked by unresolved data-safety audit issues.", file=sys.stderr)
        for blocker in blockers:
            print(f"- {blocker}", file=sys.stderr)
        raise SystemExit(1)
