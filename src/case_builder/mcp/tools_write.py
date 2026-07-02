"""Staged-write tool tier: ops enforce staging and ledger safety."""

from __future__ import annotations

from typing import Any

from ..ops import extraction as extraction_ops
from ..ops import query as query_ops
from ..ops import sources as source_ops
from .context import ServerContext, error_dict, resolve_case


def discover_sources_tool(ctx: ServerContext, case: str, query: str, limit: int = 10) -> dict[str, Any]:
    try:
        return source_ops.discover_sources(resolve_case(ctx, case), query=query, limit=limit).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))
    except Exception as exc:
        return error_dict(f"discover_sources failed: {exc}")


def ingest_url_tool(
    ctx: ServerContext,
    case: str,
    url: str,
    title: str | None = None,
    source_type: str | None = None,
    reliability_grade: str | None = None,
) -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return source_ops.ingest_url(
        ctx.runner,
        case_dir,
        url,
        title=title,
        source_type=source_type,
        reliability_grade=reliability_grade,
    ).to_dict()


def add_source_tool(
    ctx: ServerContext,
    case: str,
    title: str,
    url: str | None = None,
    source_type: str | None = None,
    reliability_grade: str | None = None,
) -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return source_ops.add_source(
        ctx.runner,
        case_dir,
        title=title,
        url=url,
        source_type=source_type,
        reliability_grade=reliability_grade,
    ).to_dict()


def parse_source_tool(ctx: ServerContext, case: str, source_id: str) -> dict[str, Any]:
    try:
        return source_ops.parse_source(resolve_case(ctx, case), source_id).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))
    except RuntimeError as exc:
        return error_dict(str(exc))


def ocr_source_tool(ctx: ServerContext, case: str, source_id: str, language: str = "eng") -> dict[str, Any]:
    try:
        return source_ops.ocr_source(resolve_case(ctx, case), source_id, language=language).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))
    except RuntimeError as exc:
        return error_dict(str(exc))


def draft_extraction_tool(ctx: ServerContext, case: str, source_id: str, template: str = "generic") -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return extraction_ops.draft_extraction(ctx.runner, case_dir, source_id, template=template).to_dict()


def save_extraction_packet_tool(ctx: ServerContext, case: str, packet_name: str, packet: dict) -> dict[str, Any]:
    try:
        return extraction_ops.save_packet(resolve_case(ctx, case), packet_name, packet).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))


def link_names_tool(ctx: ServerContext, case: str, names: list[str]) -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return query_ops.link_names(ctx.runner, case_dir, names=names).to_dict()


def plan_public_records_tool(
    ctx: ServerContext,
    case: str,
    subject: str,
    lanes: list[str] | None = None,
) -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return source_ops.plan_public_records(ctx.runner, case_dir, subject, lanes or []).to_dict()


def register(mcp: Any, ctx: ServerContext) -> None:
    @mcp.tool()
    def discover_sources(case: str, query: str, limit: int = 10) -> dict:
        """Search local SearXNG for lead-only source candidates."""
        return discover_sources_tool(ctx, case, query, limit)

    @mcp.tool()
    def ingest_url(
        case: str,
        url: str,
        title: str | None = None,
        source_type: str | None = None,
        reliability_grade: str | None = None,
    ) -> dict:
        """Fetch a public URL, extract text, and register it as a source."""
        return ingest_url_tool(ctx, case, url, title, source_type, reliability_grade)

    @mcp.tool()
    def add_source(
        case: str,
        title: str,
        url: str | None = None,
        source_type: str | None = None,
        reliability_grade: str | None = None,
    ) -> dict:
        """Register a source manually with publication metadata."""
        return add_source_tool(ctx, case, title, url, source_type, reliability_grade)

    @mcp.tool()
    def parse_source(case: str, source_id: str) -> dict:
        """Parse a registered source's raw file to text with Docling."""
        return parse_source_tool(ctx, case, source_id)

    @mcp.tool()
    def ocr_source(case: str, source_id: str, language: str = "eng") -> dict:
        """OCR a registered PDF source with OCRmyPDF."""
        return ocr_source_tool(ctx, case, source_id, language)

    @mcp.tool()
    def draft_extraction(case: str, source_id: str, template: str = "generic") -> dict:
        """Create a structured extraction packet template for a source in staging/."""
        return draft_extraction_tool(ctx, case, source_id, template)

    @mcp.tool()
    def save_extraction_packet(case: str, packet_name: str, packet: dict) -> dict:
        """Save a filled extraction packet to staging/; not a canonical import."""
        return save_extraction_packet_tool(ctx, case, packet_name, packet)

    @mcp.tool()
    def link_names(case: str, names: list[str]) -> dict:
        """Link names to existing events/co-mentions without guilt inference."""
        return link_names_tool(ctx, case, names)

    @mcp.tool()
    def plan_public_records(case: str, subject: str, lanes: list[str] | None = None) -> dict:
        """Write a public-record source-lane plan for a subject into staging/."""
        return plan_public_records_tool(ctx, case, subject, lanes)
