"""Small importable SDK recipes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from os import PathLike
from pathlib import Path
from typing import Any

from crime_research_kit.sdk import CrkClient, CrkContext, OperationResult

PathValue = str | PathLike[str] | Path
DEFAULT_EXAMPLE_CASE = "synthetic_case"


def case_info_example(
    *,
    cases_root: PathValue = Path("data/examples"),
    case_slug: str = DEFAULT_EXAMPLE_CASE,
    repo_root: PathValue | None = None,
    include_private: bool = False,
) -> OperationResult:
    """Read public-safe case metadata and record counts."""
    return _client(cases_root, repo_root=repo_root).case(case_slug).info(include_private=include_private)


def source_ingest_dry_run_example(
    url: str,
    *,
    cases_root: PathValue = Path("data/cases"),
    case_slug: str,
    repo_root: PathValue | None = None,
    title: str | None = None,
    source_type: str = "news_article",
    public_export: bool = True,
) -> OperationResult:
    """Plan URL ingestion without fetching the URL or writing case records."""
    return _client(cases_root, repo_root=repo_root, dry_run=True).case(case_slug).sources.ingest_url(
        url,
        title=title,
        source_type=source_type,
        public_export=public_export,
    )


def packet_review_example(
    packet_name: str,
    *,
    cases_root: PathValue = Path("data/cases"),
    case_slug: str,
    repo_root: PathValue | None = None,
) -> OperationResult:
    """Read a staged extraction packet for human review."""
    return _client(cases_root, repo_root=repo_root).case(case_slug).extractions.read(packet_name)


def public_safe_export_example(
    *,
    cases_root: PathValue = Path("data/cases"),
    case_slug: str,
    repo_root: PathValue | None = None,
) -> OperationResult:
    """Plan a public-safe Manim CSV export with private rows excluded."""
    return _client(cases_root, repo_root=repo_root, dry_run=True).case(case_slug).exports.manim(include_private=False)


def workflow_resume_example(
    *,
    cases_root: PathValue = Path("data/cases"),
    case_slug: str,
    thread_id: str,
    approved_packets: Sequence[str] = (),
    rejected_packets: Sequence[str | Mapping[str, Any]] = (),
    export_approved: bool = False,
    repo_root: PathValue | None = None,
) -> OperationResult:
    """Resume a workflow after explicit packet/export review decisions."""
    return _client(cases_root, repo_root=repo_root, dry_run=True).workflows.resume(
        case_slug,
        thread_id=thread_id,
        approved_packets=tuple(approved_packets),
        rejected_packets=tuple(rejected_packets),
        export_approved=export_approved,
    )


def _client(cases_root: PathValue, *, repo_root: PathValue | None, dry_run: bool = False) -> CrkClient:
    return CrkClient(CrkContext(repo_root=repo_root, cases_root=cases_root, dry_run=dry_run))
