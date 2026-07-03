"""Gated tool tier: canonical import and public exports."""

from __future__ import annotations

from typing import Any

from crime_research_kit.sdk.results import OperationResult

from crime_research_kit._runtime.adapters.interfaces.mcp.context import ServerContext, error_dict, mcp_result, sdk_case
from crime_research_kit._runtime.adapters.interfaces.mcp.tools.registry import catalog_tool

PUBLIC_NOTE = "public-safe: records with public_export=false were excluded"
PRIVATE_NOTE = "include_private=true: for internal review only, do not publish"


def import_extraction_tool(ctx: ServerContext, case: str, packet: str, confirm: bool = False) -> dict[str, Any]:
    if "/" in packet or "\\" in packet or packet.startswith("."):
        return error_dict(f"Packet must be a bare filename under staging/extractions/, got: {packet!r}")
    try:
        result = sdk_case(ctx, case).extractions.import_reviewed(packet, approved=confirm)
    except ValueError as exc:
        return error_dict(str(exc))
    return mcp_result(result)


def _export(result: OperationResult, include_private: bool) -> dict[str, Any]:
    payload = mcp_result(result)
    payload.setdefault("data", {})
    payload["data"]["privacy"] = PRIVATE_NOTE if include_private else PUBLIC_NOTE
    return payload


def export_manim_tool(ctx: ServerContext, case: str, include_private: bool = False) -> dict[str, Any]:
    try:
        result = sdk_case(ctx, case).exports.manim(include_private=include_private)
    except ValueError as exc:
        return error_dict(str(exc))
    return _export(result, include_private)


def export_case_charts_tool(ctx: ServerContext, case: str, include_private: bool = False) -> dict[str, Any]:
    try:
        result = sdk_case(ctx, case).exports.case_charts(include_private=include_private)
    except ValueError as exc:
        return error_dict(str(exc))
    return _export(result, include_private)


def export_analysis_charts_tool(ctx: ServerContext, case: str, include_private: bool = False) -> dict[str, Any]:
    try:
        result = sdk_case(ctx, case).exports.analysis_charts(include_private=include_private)
    except ValueError as exc:
        return error_dict(str(exc))
    return _export(result, include_private)


def register(mcp: Any, ctx: ServerContext) -> None:
    @catalog_tool(mcp, "gated", "import_extraction")
    def import_extraction(case: str, packet: str, confirm: bool = False) -> dict:
        """Import a staged packet into canonical records. GATED: requires confirm=true."""
        return import_extraction_tool(ctx, case, packet, confirm)

    @catalog_tool(mcp, "gated", "export_manim")
    def export_manim(case: str, include_private: bool = False) -> dict:
        """Export public-safe Manim CSVs. include_private is internal review only."""
        return export_manim_tool(ctx, case, include_private)

    @catalog_tool(mcp, "gated", "export_case_charts")
    def export_case_charts(case: str, include_private: bool = False) -> dict:
        """Export people graph and subcase timeline charts, public-safe by default."""
        return export_case_charts_tool(ctx, case, include_private)

    @catalog_tool(mcp, "gated", "export_analysis_charts")
    def export_analysis_charts(case: str, include_private: bool = False) -> dict:
        """Export extended analysis charts, public-safe by default."""
        return export_analysis_charts_tool(ctx, case, include_private)
