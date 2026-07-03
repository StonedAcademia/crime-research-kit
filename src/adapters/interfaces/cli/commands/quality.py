"""Typer commands for ledger quality and review gates."""

from __future__ import annotations

import typer

from adapters.interfaces.cli.commands import choice_enum, dispatch, enum_value
from adapters.ops.evidence.quality import contradictions, dedupe, identity, preservation
from adapters.ops.evidence.quality.safety import privacy, public_export, readiness, source_independence

app = typer.Typer(no_args_is_help=True)

RecordType = choice_enum("RecordType", ["all", "entities", "sources", "claims"])


@app.command("dedupe", help="Report duplicate candidate entities, sources, or claims")
def dedupe_records(
    case_dir: str = typer.Argument(...),
    record_type: RecordType = typer.Option(RecordType("all"), "--record-type"),
    min_key_chars: int = typer.Option(12, "--min-key-chars"),
    out: str | None = typer.Option(None, "--out", "--output"),
) -> None:
    dispatch(dedupe.dedupe, case_dir=case_dir, record_type=enum_value(record_type), min_key_chars=min_key_chars, out=out)


@app.command("preserve-source", help="Hash and report preservation metadata for an existing source")
def preserve_source(
    case_dir: str = typer.Argument(...),
    source_id: str = typer.Argument(...),
    archive_url: str | None = typer.Option(None, "--archive-url"),
    content_type: str | None = typer.Option(None, "--content-type"),
    out: str | None = typer.Option(None, "--out", "--output"),
) -> None:
    dispatch(
        preservation.preserve_source,
        case_dir=case_dir,
        source_id=source_id,
        archive_url=archive_url,
        content_type=content_type,
        out=out,
    )


@app.command("resolve-identities", help="Report candidate duplicate or ambiguous identity records without merging")
def resolve_identities(
    case_dir: str = typer.Argument(...),
    min_key_chars: int = typer.Option(8, "--min-key-chars"),
    include_merged: bool = typer.Option(False, "--include-merged"),
    out: str | None = typer.Option(None, "--out", "--output"),
) -> None:
    dispatch(
        identity.resolve_identities,
        case_dir=case_dir,
        min_key_chars=min_key_chars,
        include_merged=include_merged,
        out=out,
    )


@app.command("audit-contradictions", help="Report explicit and likely claim contradictions without mutating claims")
def audit_contradictions(
    case_dir: str = typer.Argument(...),
    out: str | None = typer.Option(None, "--out", "--output"),
    include_private: bool = typer.Option(False, "--include-private"),
    min_overlap: float = typer.Option(0.45, "--min-overlap"),
    fail_on_flags: bool = typer.Option(False, "--fail-on-flags"),
) -> None:
    dispatch(
        contradictions.audit_contradictions,
        case_dir=case_dir,
        out=out,
        include_private=include_private,
        min_overlap=min_overlap,
        fail_on_flags=fail_on_flags,
    )


@app.command(
    "review-narrative-readiness",
    help="Report public narrative readiness gaps across claims, events, and relationships",
)
def review_narrative_readiness(
    case_dir: str = typer.Argument(...),
    include_private: bool = typer.Option(False, "--include-private"),
    require_spans: bool = typer.Option(False, "--require-spans"),
    min_independent_sources: int = typer.Option(2, "--min-independent-sources"),
    fail_on_blockers: bool = typer.Option(False, "--fail-on-blockers"),
    out: str | None = typer.Option(None, "--out", "--output"),
) -> None:
    dispatch(
        readiness.review_narrative_readiness,
        case_dir=case_dir,
        include_private=include_private,
        require_spans=require_spans,
        min_independent_sources=min_independent_sources,
        fail_on_blockers=fail_on_blockers,
        out=out,
    )


@app.command("audit-privacy-redactions", help="Report privacy and redaction issues before public output")
def audit_privacy_redactions(
    case_dir: str = typer.Argument(...),
    include_private: bool = typer.Option(False, "--include-private"),
    require_redaction_log: bool = typer.Option(False, "--require-redaction-log"),
    warn_only: bool = typer.Option(False, "--warn-only"),
    out: str | None = typer.Option(None, "--out", "--output"),
) -> None:
    dispatch(
        privacy.audit_privacy_redactions,
        case_dir=case_dir,
        include_private=include_private,
        require_redaction_log=require_redaction_log,
        warn_only=warn_only,
        out=out,
    )


@app.command("audit-public-export", help="Fail if public exports include unsafe or unsupported records")
def audit_public_export(
    case_dir: str = typer.Argument(...),
    out: str | None = typer.Option(None, "--out", "--output"),
    warn_only: bool = typer.Option(False, "--warn-only"),
) -> None:
    dispatch(public_export.audit_public_export, case_dir=case_dir, out=out, warn_only=warn_only)


@app.command("source-independence", hidden=True)
@app.command(
    "audit-source-independence",
    help="Report source-chain, wire-copy, and press-release independence risks",
)
def audit_source_independence(
    case_dir: str = typer.Argument(...),
    out: str | None = typer.Option(None, "--out", "--output"),
    include_private: bool = typer.Option(False, "--include-private"),
    min_title_chars: int = typer.Option(16, "--min-title-chars"),
    fail_on_flags: bool = typer.Option(False, "--fail-on-flags"),
) -> None:
    dispatch(
        source_independence.source_independence,
        case_dir=case_dir,
        out=out,
        include_private=include_private,
        min_title_chars=min_title_chars,
        fail_on_flags=fail_on_flags,
    )
