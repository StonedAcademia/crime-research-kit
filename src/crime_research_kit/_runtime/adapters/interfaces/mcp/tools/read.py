"""Read/query tool tier: always available, never writes canonical records."""

from __future__ import annotations

from typing import Any

from crime_research_kit._runtime.adapters.interfaces.mcp.context import ServerContext, error_dict, mcp_result, resolve_case, sdk_case, sdk_client
from crime_research_kit._runtime.adapters.interfaces.mcp.tools.registry import catalog_tool, direct_tool
from crime_research_kit._runtime.adapters.ops import case as case_ops


def case_info_tool(ctx: ServerContext, case: str) -> dict[str, Any]:
    try:
        return mcp_result(sdk_case(ctx, case).info())
    except ValueError as exc:
        return error_dict(str(exc))


def list_cases_tool(ctx: ServerContext) -> dict[str, Any]:
    result = sdk_client(ctx).cases.list()
    return {"ok": result.ok, "cases": result.data.get("cases", [])}


def get_records_tool(
    ctx: ServerContext,
    case: str,
    record_type: str,
    include_private: bool = False,
    limit: int = 200,
) -> dict[str, Any]:
    try:
        result = sdk_case(ctx, case).records.list(record_type, include_private=include_private, limit=limit)
    except ValueError as exc:
        return error_dict(str(exc))
    return mcp_result(result)


def get_source_text_tool(
    ctx: ServerContext,
    case: str,
    source_id: str,
    include_private: bool = False,
    max_chars: int = 20000,
) -> dict[str, Any]:
    try:
        result = sdk_case(ctx, case).records.source_text(source_id, include_private=include_private, max_chars=max_chars)
        return mcp_result(result)
    except ValueError as exc:
        return error_dict(str(exc))


def query_case_tool(
    ctx: ServerContext,
    case: str,
    query: str,
    include_private: bool = False,
    top_k: int = 8,
) -> dict[str, Any]:
    try:
        result = sdk_case(ctx, case).retrieval.query(
            include_private=include_private,
            query_text=query,
            top_k=top_k,
        )
        return mcp_result(result)
    except ValueError as exc:
        return error_dict(str(exc))


def list_staged_packets_tool(ctx: ServerContext, case: str) -> dict[str, Any]:
    try:
        return mcp_result(sdk_case(ctx, case).extractions.list())
    except ValueError as exc:
        return error_dict(str(exc))


def run_report_tool(ctx: ServerContext, case: str) -> dict[str, Any]:
    try:
        return case_ops.report(ctx.runner, resolve_case(ctx, case)).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))


def register(mcp: Any, ctx: ServerContext) -> None:
    @catalog_tool(mcp, "read", "case_info")
    def case_info(case: str) -> dict:
        """Case metadata and per-record-type counts for a CRK case slug."""
        return case_info_tool(ctx, case)

    @catalog_tool(mcp, "read", "list_cases")
    def list_cases() -> dict:
        """List available CRK case slugs."""
        return list_cases_tool(ctx)

    @catalog_tool(mcp, "read", "get_records")
    def get_records(case: str, record_type: str, include_private: bool = False, limit: int = 200) -> dict:
        """Read ledger records. Private records are excluded unless include_private."""
        return get_records_tool(ctx, case, record_type, include_private, limit)

    @catalog_tool(mcp, "read", "get_source_text")
    def get_source_text(case: str, source_id: str, include_private: bool = False, max_chars: int = 20000) -> dict:
        """Read the extracted text of a registered source."""
        return get_source_text_tool(ctx, case, source_id, include_private, max_chars)

    @catalog_tool(mcp, "read", "query_case")
    def query_case(case: str, query: str, include_private: bool = False, top_k: int = 8) -> dict:
        """Semantic retrieval over the local case evidence index."""
        return query_case_tool(ctx, case, query, include_private, top_k)

    @catalog_tool(mcp, "read", "list_staged_packets")
    def list_staged_packets(case: str) -> dict:
        """List extraction packets staged for human review."""
        return list_staged_packets_tool(ctx, case)

    @direct_tool(mcp, "read", "run_report")
    def run_report(case: str) -> dict:
        """Write the case evidence-board Markdown report."""
        return run_report_tool(ctx, case)
