from __future__ import annotations

from pathlib import Path

from crime_research_kit.sdk import CrkClient, CrkContext
from crime_research_kit.sdk.errors import INVALID_INPUT
from tests.helpers import KIT_ROOT, ledger_command_args, ledger_subcommand


def dry_case(case_dir: Path):
    client = CrkClient(CrkContext(repo_root=KIT_ROOT, cases_root=case_dir.parent, dry_run=True))
    return client.case("synthetic_case")


def test_review_validate_plans_command(synthetic_case_copy: Path):
    result = dry_case(synthetic_case_copy).review.validate()

    assert result.ok is True
    assert result.operation == "review.validate"
    assert ledger_command_args(result.diagnostics["command"]) == ["validate", str(synthetic_case_copy)]


def test_review_dedupe_plans_record_type_and_output(synthetic_case_copy: Path):
    result = dry_case(synthetic_case_copy).review.dedupe(
        record_type="claims",
        min_key_chars=7,
        out="staging/candidates/custom_dedupe.json",
    )

    args = ledger_command_args(result.diagnostics["command"])
    assert result.ok is True
    assert result.operation == "review.dedupe"
    assert args[:2] == ["dedupe", str(synthetic_case_copy)]
    assert args[args.index("--record-type") + 1] == "claims"
    assert args[args.index("--min-key-chars") + 1] == "7"
    assert args[args.index("--out") + 1] == "staging/candidates/custom_dedupe.json"


def test_review_dedupe_validates_record_type(synthetic_case_copy: Path):
    result = dry_case(synthetic_case_copy).review.dedupe(record_type="events")

    assert result.ok is False
    assert result.operation == "review.dedupe"
    assert result.errors[0].code == INVALID_INPUT


def test_review_resolve_identities_plans_include_merged(synthetic_case_copy: Path):
    result = dry_case(synthetic_case_copy).review.resolve_identities(min_key_chars=5, include_merged=True)

    args = ledger_command_args(result.diagnostics["command"])
    assert result.ok is True
    assert result.operation == "review.resolve_identities"
    assert args[:2] == ["resolve-identities", str(synthetic_case_copy)]
    assert args[args.index("--min-key-chars") + 1] == "5"
    assert "--include-merged" in args


def test_review_audit_contradictions_uses_privacy_default(synthetic_case_copy: Path):
    case = dry_case(synthetic_case_copy).with_privacy(include_private=True)

    result = case.review.audit_contradictions(min_overlap=0.5, fail_on_flags=True)

    args = ledger_command_args(result.diagnostics["command"])
    assert result.operation == "review.audit_contradictions"
    assert ledger_subcommand(result.diagnostics["command"]) == "audit-contradictions"
    assert args[args.index("--min-overlap") + 1] == "0.5"
    assert "--include-private" in args
    assert "--fail-on-flags" in args


def test_review_narrative_readiness_plans_gate_options(synthetic_case_copy: Path):
    result = dry_case(synthetic_case_copy).review.narrative_readiness(
        require_spans=True,
        min_independent_sources=3,
        fail_on_blockers=True,
    )

    args = ledger_command_args(result.diagnostics["command"])
    assert result.operation == "review.narrative_readiness"
    assert ledger_subcommand(result.diagnostics["command"]) == "review-narrative-readiness"
    assert args[args.index("--min-independent-sources") + 1] == "3"
    assert "--require-spans" in args
    assert "--fail-on-blockers" in args


def test_review_privacy_redactions_plans_warn_only(synthetic_case_copy: Path):
    result = dry_case(synthetic_case_copy).review.audit_privacy_redactions(
        include_private=True,
        require_redaction_log=True,
        warn_only=True,
    )

    args = ledger_command_args(result.diagnostics["command"])
    assert result.operation == "review.audit_privacy_redactions"
    assert ledger_subcommand(result.diagnostics["command"]) == "audit-privacy-redactions"
    assert "--include-private" in args
    assert "--require-redaction-log" in args
    assert "--warn-only" in args


def test_review_public_export_plans_warn_only(synthetic_case_copy: Path):
    result = dry_case(synthetic_case_copy).review.audit_public_export(warn_only=True, out="exports/public_audit.json")

    args = ledger_command_args(result.diagnostics["command"])
    assert result.operation == "review.audit_public_export"
    assert ledger_subcommand(result.diagnostics["command"]) == "audit-public-export"
    assert "--warn-only" in args
    assert args[args.index("--out") + 1] == "exports/public_audit.json"


def test_review_source_independence_plans_thresholds(synthetic_case_copy: Path):
    result = dry_case(synthetic_case_copy).review.audit_source_independence(
        include_private=True,
        min_title_chars=11,
        fail_on_flags=True,
    )

    args = ledger_command_args(result.diagnostics["command"])
    assert result.operation == "review.audit_source_independence"
    assert ledger_subcommand(result.diagnostics["command"]) == "audit-source-independence"
    assert args[args.index("--min-title-chars") + 1] == "11"
    assert "--include-private" in args
    assert "--fail-on-flags" in args


def test_review_validates_positive_thresholds(synthetic_case_copy: Path):
    result = dry_case(synthetic_case_copy).review.narrative_readiness(min_independent_sources=0)

    assert result.ok is False
    assert result.operation == "review.narrative_readiness"
    assert result.errors[0].code == INVALID_INPUT
