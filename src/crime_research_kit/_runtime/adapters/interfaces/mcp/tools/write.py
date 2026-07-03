"""Staged-write tool tier: ops enforce staging and ledger safety."""

from __future__ import annotations

from typing import Any

from crime_research_kit._runtime.adapters.interfaces.mcp.context import ServerContext, error_dict, mcp_result, sdk_case
from crime_research_kit._runtime.adapters.interfaces.mcp.tools.registry import catalog_tool


def discover_sources_tool(ctx: ServerContext, case: str, query: str, limit: int = 10) -> dict[str, Any]:
    try:
        return mcp_result(sdk_case(ctx, case).sources.discover(query=query, limit=limit))
    except ValueError as exc:
        return error_dict(str(exc))


def ingest_url_tool(
    ctx: ServerContext,
    case: str,
    url: str,
    title: str | None = None,
    source_type: str | None = None,
    reliability_grade: str | None = None,
) -> dict[str, Any]:
    try:
        result = sdk_case(ctx, case).sources.ingest_url(
            url,
            title=title,
            source_type=source_type,
            reliability_grade=reliability_grade,
        )
    except ValueError as exc:
        return error_dict(str(exc))
    return mcp_result(result)


def add_source_tool(
    ctx: ServerContext,
    case: str,
    title: str,
    url: str | None = None,
    source_type: str | None = None,
    reliability_grade: str | None = None,
) -> dict[str, Any]:
    try:
        result = sdk_case(ctx, case).sources.add(
            title=title,
            url=url,
            source_type=source_type,
            reliability_grade=reliability_grade,
        )
    except ValueError as exc:
        return error_dict(str(exc))
    return mcp_result(result)


def parse_source_tool(ctx: ServerContext, case: str, source_id: str) -> dict[str, Any]:
    try:
        return mcp_result(sdk_case(ctx, case).sources.parse(source_id))
    except ValueError as exc:
        return error_dict(str(exc))


def ocr_source_tool(ctx: ServerContext, case: str, source_id: str, language: str = "eng") -> dict[str, Any]:
    try:
        return mcp_result(sdk_case(ctx, case).sources.ocr(source_id, language=language))
    except ValueError as exc:
        return error_dict(str(exc))


def draft_extraction_tool(ctx: ServerContext, case: str, source_id: str, template: str = "generic") -> dict[str, Any]:
    try:
        result = sdk_case(ctx, case).extractions.draft(source_id, template=template)
    except ValueError as exc:
        return error_dict(str(exc))
    return mcp_result(result)


def save_extraction_packet_tool(ctx: ServerContext, case: str, packet_name: str, packet: dict) -> dict[str, Any]:
    try:
        return mcp_result(sdk_case(ctx, case).extractions.save(packet_name, packet))
    except ValueError as exc:
        return error_dict(str(exc))


def link_names_tool(ctx: ServerContext, case: str, names: list[str]) -> dict[str, Any]:
    try:
        result = sdk_case(ctx, case).names.link(names=names)
    except ValueError as exc:
        return error_dict(str(exc))
    return mcp_result(result)


def plan_public_records_tool(
    ctx: ServerContext,
    case: str,
    subject: str,
    lanes: list[str] | None = None,
) -> dict[str, Any]:
    try:
        result = sdk_case(ctx, case).records.plan_public_records(subject, lanes=lanes or [])
    except ValueError as exc:
        return error_dict(str(exc))
    return mcp_result(result)


def register(mcp: Any, ctx: ServerContext) -> None:
    @catalog_tool(mcp, "write", "discover_sources")
    def discover_sources(case: str, query: str, limit: int = 10) -> dict:
        """Search local SearXNG for lead-only source candidates."""
        return discover_sources_tool(ctx, case, query, limit)

    @catalog_tool(mcp, "write", "ingest_url")
    def ingest_url(
        case: str,
        url: str,
        title: str | None = None,
        source_type: str | None = None,
        reliability_grade: str | None = None,
    ) -> dict:
        """Fetch a public URL, extract text, and register it as a source."""
        return ingest_url_tool(ctx, case, url, title, source_type, reliability_grade)

    @catalog_tool(mcp, "write", "add_source")
    def add_source(
        case: str,
        title: str,
        url: str | None = None,
        source_type: str | None = None,
        reliability_grade: str | None = None,
    ) -> dict:
        """Register a source manually with publication metadata."""
        return add_source_tool(ctx, case, title, url, source_type, reliability_grade)

    @catalog_tool(mcp, "write", "parse_source")
    def parse_source(case: str, source_id: str) -> dict:
        """Parse a registered source's raw file to text with Docling."""
        return parse_source_tool(ctx, case, source_id)

    @catalog_tool(mcp, "write", "ocr_source")
    def ocr_source(case: str, source_id: str, language: str = "eng") -> dict:
        """OCR a registered PDF source with OCRmyPDF."""
        return ocr_source_tool(ctx, case, source_id, language)

    @catalog_tool(mcp, "write", "draft_extraction")
    def draft_extraction(case: str, source_id: str, template: str = "generic") -> dict:
        """Create a structured extraction packet template for a source in staging/."""
        return draft_extraction_tool(ctx, case, source_id, template)

    @catalog_tool(mcp, "write", "save_extraction_packet")
    def save_extraction_packet(case: str, packet_name: str, packet: dict) -> dict:
        """Save a filled extraction packet to staging/; not a canonical import."""
        return save_extraction_packet_tool(ctx, case, packet_name, packet)

    @catalog_tool(mcp, "write", "link_names")
    def link_names(case: str, names: list[str]) -> dict:
        """Link names to existing events/co-mentions without guilt inference."""
        return link_names_tool(ctx, case, names)

    @catalog_tool(mcp, "write", "plan_public_records")
    def plan_public_records(case: str, subject: str, lanes: list[str] | None = None) -> dict:
        """Write a public-record source-lane plan for a subject into staging/."""
        return plan_public_records_tool(ctx, case, subject, lanes)
