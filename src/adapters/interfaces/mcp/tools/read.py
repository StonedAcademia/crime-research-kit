"""Read/query tool tier: always available, never writes canonical records."""

from __future__ import annotations

from typing import Any

from adapters.interfaces.mcp.context import ServerContext, error_dict, list_case_slugs, resolve_case
from adapters.ops import case as case_ops
from adapters.ops import extraction as extraction_ops
from adapters.ops import query as query_ops


def case_info_tool(ctx: ServerContext, case: str) -> dict[str, Any]:
    try:
        return case_ops.case_info(resolve_case(ctx, case)).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))


def list_cases_tool(ctx: ServerContext) -> dict[str, Any]:
    return {"ok": True, "cases": list_case_slugs(ctx)}


def get_records_tool(
    ctx: ServerContext,
    case: str,
    record_type: str,
    include_private: bool = False,
    limit: int = 200,
) -> dict[str, Any]:
    try:
        result = query_ops.get_records(resolve_case(ctx, case), record_type, include_private=include_private)
    except ValueError as exc:
        return error_dict(str(exc))
    if result.ok and limit and len(result.data["records"]) > limit:
        result.data["records"] = result.data["records"][:limit]
        result.data["truncated"] = True
    return result.to_dict()


def get_source_text_tool(
    ctx: ServerContext,
    case: str,
    source_id: str,
    include_private: bool = False,
    max_chars: int = 20000,
) -> dict[str, Any]:
    try:
        return query_ops.get_source_text(
            resolve_case(ctx, case),
            source_id,
            include_private=include_private,
            max_chars=max_chars,
        ).to_dict()
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
        return query_ops.query_case(
            resolve_case(ctx, case),
            query,
            include_private=include_private,
            top_k=top_k,
        ).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))
    except Exception as exc:
        return error_dict(f"query_case failed: {exc}")


def list_staged_packets_tool(ctx: ServerContext, case: str) -> dict[str, Any]:
    try:
        return extraction_ops.list_packets(resolve_case(ctx, case)).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))


def run_report_tool(ctx: ServerContext, case: str) -> dict[str, Any]:
    try:
        return case_ops.report(ctx.runner, resolve_case(ctx, case)).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))


def register(mcp: Any, ctx: ServerContext) -> None:
    @mcp.tool()
    def case_info(case: str) -> dict:
        """Case metadata and per-record-type counts for a CRK case slug."""
        return case_info_tool(ctx, case)

    @mcp.tool()
    def list_cases() -> dict:
        """List available CRK case slugs."""
        return list_cases_tool(ctx)

    @mcp.tool()
    def get_records(case: str, record_type: str, include_private: bool = False, limit: int = 200) -> dict:
        """Read ledger records. Private records are excluded unless include_private."""
        return get_records_tool(ctx, case, record_type, include_private, limit)

    @mcp.tool()
    def get_source_text(case: str, source_id: str, include_private: bool = False, max_chars: int = 20000) -> dict:
        """Read the extracted text of a registered source."""
        return get_source_text_tool(ctx, case, source_id, include_private, max_chars)

    @mcp.tool()
    def query_case(case: str, query: str, include_private: bool = False, top_k: int = 8) -> dict:
        """Semantic retrieval over the local case evidence index."""
        return query_case_tool(ctx, case, query, include_private, top_k)

    @mcp.tool()
    def list_staged_packets(case: str) -> dict:
        """List extraction packets staged for human review."""
        return list_staged_packets_tool(ctx, case)

    @mcp.tool()
    def run_report(case: str) -> dict:
        """Write the case evidence-board Markdown report."""
        return run_report_tool(ctx, case)
