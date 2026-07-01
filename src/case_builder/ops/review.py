"""Deterministic review audits over the case ledger."""

from __future__ import annotations

from .result import OpResult
from .runner import TrcrRunner


def audit_contradictions(runner: TrcrRunner, case_dir: str) -> OpResult:
    return runner.run("audit_contradictions", ["audit-contradictions", case_dir])


def review_narrative_readiness(runner: TrcrRunner, case_dir: str) -> OpResult:
    return runner.run("review_narrative_readiness", ["review-narrative-readiness", case_dir])


def audit_privacy_redactions(runner: TrcrRunner, case_dir: str) -> OpResult:
    return runner.run("audit_privacy_redactions", ["audit-privacy-redactions", case_dir])


def audit_public_export(runner: TrcrRunner, case_dir: str) -> OpResult:
    return runner.run("audit_public_export", ["audit-public-export", case_dir])


def audit_source_independence(runner: TrcrRunner, case_dir: str) -> OpResult:
    return runner.run("audit_source_independence", ["audit-source-independence", case_dir])
