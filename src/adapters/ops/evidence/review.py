"""Deterministic review audits over the case ledger."""

from __future__ import annotations

from adapters.ops.result import OpResult
from adapters.ops.runner import CrkRunner


def dedupe(runner: CrkRunner, case_dir: str, *, record_type: str = "all", min_key_chars: int = 12, out: str | None = None) -> OpResult:
    args = ["dedupe", case_dir, "--record-type", record_type, "--min-key-chars", str(min_key_chars)]
    _option(args, "--out", out)
    return runner.run("dedupe", args)


def resolve_identities(
    runner: CrkRunner,
    case_dir: str,
    *,
    min_key_chars: int = 8,
    include_merged: bool = False,
    out: str | None = None,
) -> OpResult:
    args = ["resolve-identities", case_dir, "--min-key-chars", str(min_key_chars)]
    _flag(args, "--include-merged", include_merged)
    _option(args, "--out", out)
    return runner.run("resolve_identities", args)


def audit_contradictions(
    runner: CrkRunner,
    case_dir: str,
    *,
    out: str | None = None,
    include_private: bool = False,
    min_overlap: float = 0.45,
    fail_on_flags: bool = False,
) -> OpResult:
    args = ["audit-contradictions", case_dir, "--min-overlap", str(min_overlap)]
    _flag(args, "--include-private", include_private)
    _flag(args, "--fail-on-flags", fail_on_flags)
    _option(args, "--out", out)
    return runner.run("audit_contradictions", args)


def review_narrative_readiness(
    runner: CrkRunner,
    case_dir: str,
    *,
    include_private: bool = False,
    require_spans: bool = False,
    min_independent_sources: int = 2,
    fail_on_blockers: bool = False,
    out: str | None = None,
) -> OpResult:
    args = ["review-narrative-readiness", case_dir, "--min-independent-sources", str(min_independent_sources)]
    _flag(args, "--include-private", include_private)
    _flag(args, "--require-spans", require_spans)
    _flag(args, "--fail-on-blockers", fail_on_blockers)
    _option(args, "--out", out)
    return runner.run("review_narrative_readiness", args)


def audit_privacy_redactions(
    runner: CrkRunner,
    case_dir: str,
    *,
    include_private: bool = False,
    require_redaction_log: bool = False,
    warn_only: bool = False,
    out: str | None = None,
) -> OpResult:
    args = ["audit-privacy-redactions", case_dir]
    _flag(args, "--include-private", include_private)
    _flag(args, "--require-redaction-log", require_redaction_log)
    _flag(args, "--warn-only", warn_only)
    _option(args, "--out", out)
    return runner.run("audit_privacy_redactions", args)


def audit_public_export(runner: CrkRunner, case_dir: str, *, out: str | None = None, warn_only: bool = False) -> OpResult:
    args = ["audit-public-export", case_dir]
    _flag(args, "--warn-only", warn_only)
    _option(args, "--out", out)
    return runner.run("audit_public_export", args)


def audit_source_independence(
    runner: CrkRunner,
    case_dir: str,
    *,
    out: str | None = None,
    include_private: bool = False,
    min_title_chars: int = 16,
    fail_on_flags: bool = False,
) -> OpResult:
    args = ["audit-source-independence", case_dir, "--min-title-chars", str(min_title_chars)]
    _flag(args, "--include-private", include_private)
    _flag(args, "--fail-on-flags", fail_on_flags)
    _option(args, "--out", out)
    return runner.run("audit_source_independence", args)


def _flag(args: list[str], name: str, enabled: bool) -> None:
    if enabled:
        args.append(name)


def _option(args: list[str], name: str, value: str | None) -> None:
    if value is not None:
        args.extend([name, value])
