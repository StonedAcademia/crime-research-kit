"""Gated tool tier: canonical import and public exports."""

from __future__ import annotations

from typing import Any

from ..ops import exports as export_ops
from ..ops import extraction as extraction_ops
from .context import ServerContext, error_dict, resolve_case

PUBLIC_NOTE = "public-safe: records with public_export=false were excluded"
PRIVATE_NOTE = "include_private=true: for internal review only, do not publish"


def import_extraction_tool(ctx: ServerContext, case: str, packet: str, confirm: bool = False) -> dict[str, Any]:
    if "/" in packet or "\\" in packet or packet.startswith("."):
        return error_dict(f"Packet must be a bare filename under staging/extractions/, got: {packet!r}")
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    packet_path = f"{case_dir.rstrip('/')}/staging/extractions/{packet}"
    return extraction_ops.import_extraction(ctx.runner, case_dir, packet_path, confirm=confirm).to_dict()


def _export(result, include_private: bool) -> dict[str, Any]:
    payload = result.to_dict()
    payload.setdefault("data", {})
    payload["data"]["privacy"] = PRIVATE_NOTE if include_private else PUBLIC_NOTE
    return payload


def export_manim_tool(ctx: ServerContext, case: str, include_private: bool = False) -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return _export(export_ops.export_manim(ctx.runner, case_dir, include_private=include_private), include_private)


def export_case_charts_tool(ctx: ServerContext, case: str, include_private: bool = False) -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return _export(export_ops.export_case_charts(ctx.runner, case_dir, include_private=include_private), include_private)


def export_analysis_charts_tool(ctx: ServerContext, case: str, include_private: bool = False) -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    result = export_ops.export_analysis_charts(ctx.runner, case_dir, include_private=include_private)
    return _export(result, include_private)


def register(mcp: Any, ctx: ServerContext) -> None:
    @mcp.tool()
    def import_extraction(case: str, packet: str, confirm: bool = False) -> dict:
        """Import a staged packet into canonical records. GATED: requires confirm=true."""
        return import_extraction_tool(ctx, case, packet, confirm)

    @mcp.tool()
    def export_manim(case: str, include_private: bool = False) -> dict:
        """Export public-safe Manim CSVs. include_private is internal review only."""
        return export_manim_tool(ctx, case, include_private)

    @mcp.tool()
    def export_case_charts(case: str, include_private: bool = False) -> dict:
        """Export people graph and subcase timeline charts, public-safe by default."""
        return export_case_charts_tool(ctx, case, include_private)

    @mcp.tool()
    def export_analysis_charts(case: str, include_private: bool = False) -> dict:
        """Export extended analysis charts, public-safe by default."""
        return export_analysis_charts_tool(ctx, case, include_private)
