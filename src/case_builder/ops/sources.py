"""Source intake operations: planning, registration, discovery, parsing, OCR."""

from __future__ import annotations

from typing import Sequence

from ..acquisition import discover_sources as _discover_sources
from ..config import searxng_url as default_searxng_url
from ..parsing import ocr_source as _ocr_source
from ..parsing import parse_source as _parse_source
from .result import OpResult, local_op
from .runner import CrkRunner


def plan_public_records(runner: CrkRunner, case_dir: str, subject: str, lanes: Sequence[str]) -> OpResult:
    args = ["plan-public-records", case_dir, "--subject", subject]
    for lane in lanes:
        args.extend(["--lane", lane])
    return runner.run("plan_public_records", args)


def add_source(
    runner: CrkRunner,
    case_dir: str,
    *,
    title: str,
    url: str | None = None,
    source_type: str | None = None,
    reliability_grade: str | None = None,
    author: str | None = None,
    publisher: str | None = None,
    date_published: str | None = None,
    archive_url: str | None = None,
    notes: str | None = None,
    public_export: bool = True,
) -> OpResult:
    args = ["add-source", case_dir, "--title", title]
    args += _optional_flags(
        ("--url", url),
        ("--source-type", source_type),
        ("--reliability-grade", reliability_grade),
        ("--author", author),
        ("--publisher", publisher),
        ("--date-published", date_published),
        ("--archive-url", archive_url),
        ("--notes", notes),
    )
    if not public_export:
        args.append("--no-public-export")
    return runner.run("add_source", args)


def ingest_url(
    runner: CrkRunner,
    case_dir: str,
    url: str,
    *,
    title: str | None = None,
    source_type: str | None = None,
    reliability_grade: str | None = None,
    timeout: int | None = None,
    public_export: bool = True,
) -> OpResult:
    args = ["ingest-url", case_dir, url]
    args += _optional_flags(
        ("--title", title),
        ("--source-type", source_type),
        ("--reliability-grade", reliability_grade),
        ("--timeout", str(timeout) if timeout is not None else None),
    )
    if not public_export:
        args.append("--no-public-export")
    return runner.run("ingest_url", args)


def preserve_source(
    runner: CrkRunner,
    case_dir: str,
    source_id: str,
    *,
    archive_url: str | None = None,
    content_type: str | None = None,
    out: str | None = None,
) -> OpResult:
    args = ["preserve-source", case_dir, source_id]
    args += _optional_flags(("--archive-url", archive_url), ("--content-type", content_type), ("--out", out))
    return runner.run("preserve_source", args)


def discover_sources(
    case_dir: str,
    *,
    query: str,
    searxng_url: str | None = None,
    limit: int = 10,
    out: str | None = None,
) -> OpResult:
    return local_op(
        "discover_sources",
        _discover_sources,
        case_dir,
        query=query,
        searxng_url=default_searxng_url(searxng_url),
        limit=limit,
        out=out,
    )


def parse_source(case_dir: str, source_id: str, *, force: bool = False) -> OpResult:
    return local_op("parse_source", _parse_source, case_dir, source_id, force=force)


def ocr_source(case_dir: str, source_id: str, *, language: str = "eng", force: bool = False) -> OpResult:
    return local_op("ocr_source", _ocr_source, case_dir, source_id, language=language, force=force)


def _optional_flags(*pairs: tuple[str, str | None]) -> list[str]:
    args: list[str] = []
    for flag, value in pairs:
        if value:
            args.extend([flag, value])
    return args
