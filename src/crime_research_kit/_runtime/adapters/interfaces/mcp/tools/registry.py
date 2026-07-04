"""Catalog-backed metadata for MCP tool registration."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Callable

from crime_research_kit.sdk.operations import OperationSpec, get_operation, list_operations


@dataclass(frozen=True, slots=True)
class McpToolRegistration:
    """Metadata tying one MCP tool to the SDK catalog or a direct exception."""

    tool_name: str
    module: str
    handler_name: str
    summary: str
    operation_name: str | None = None
    direct_reason: str | None = None

    @property
    def sdk_backed(self) -> bool:
        return self.operation_name is not None

    @property
    def operation(self) -> OperationSpec | None:
        return get_operation(self.operation_name) if self.operation_name else None

    def handler(self) -> Callable[..., Any]:
        module = import_module(f"crime_research_kit._runtime.adapters.interfaces.mcp.tools.{self.module}")
        return getattr(module, self.handler_name)


_SDK_HANDLERS = {
    "case_info": ("read", "case_info_tool", "Case metadata and per-record-type counts for a CRK case slug."),
    "list_cases": ("read", "list_cases_tool", "List available CRK case slugs."),
    "get_records": (
        "read",
        "get_records_tool",
        "Read ledger records. Private records are excluded unless include_private.",
    ),
    "get_source_text": ("read", "get_source_text_tool", "Read the extracted text of a registered source."),
    "query_case": ("read", "query_case_tool", "Semantic retrieval over the local case evidence index."),
    "list_staged_packets": ("read", "list_staged_packets_tool", "List extraction packets staged for human review."),
    "discover_sources": ("write", "discover_sources_tool", "Search local SearXNG for lead-only source candidates."),
    "ingest_url": ("write", "ingest_url_tool", "Fetch a public URL, extract text, and register it as a source."),
    "add_source": ("write", "add_source_tool", "Register a source manually with publication metadata."),
    "parse_source": ("write", "parse_source_tool", "Parse a registered source's raw file to text with Docling."),
    "ocr_source": ("write", "ocr_source_tool", "OCR a registered PDF source with OCRmyPDF."),
    "draft_extraction": (
        "write",
        "draft_extraction_tool",
        "Create a structured extraction packet template for a source in staging/.",
    ),
    "save_extraction_packet": (
        "write",
        "save_extraction_packet_tool",
        "Save a filled extraction packet to staging/; not a canonical import.",
    ),
    "link_names": ("write", "link_names_tool", "Link names to existing events/co-mentions without guilt inference."),
    "plan_public_records": (
        "write",
        "plan_public_records_tool",
        "Write a public-record source-lane plan for a subject into staging/.",
    ),
    "import_extraction": (
        "gated",
        "import_extraction_tool",
        "Import a staged packet into canonical records. GATED: requires confirm=true.",
    ),
    "export_manim": (
        "gated",
        "export_manim_tool",
        "Export public-safe Manim CSVs. include_private is internal review only.",
    ),
    "export_case_visuals": (
        "gated",
        "export_case_visuals_tool",
        "Export curated case visual deck, consoles, and audit CSVs.",
    ),
}

DIRECT_TOOL_REGISTRATIONS = (
    McpToolRegistration(
        tool_name="run_report",
        module="read",
        handler_name="run_report_tool",
        summary="Write the case evidence-board Markdown report.",
        direct_reason="Derived evidence-board report lacks explicit public/private filtering semantics.",
    ),
)
DIRECT_TOOL_NAMES = frozenset(entry.tool_name for entry in DIRECT_TOOL_REGISTRATIONS)


def sdk_tool_registrations() -> tuple[McpToolRegistration, ...]:
    """Return MCP registrations derived from catalog entries with mcp_tool set."""
    specs = tuple(spec for spec in list_operations() if spec.mcp_tool)
    catalog_tools = {spec.mcp_tool for spec in specs}
    missing = catalog_tools - set(_SDK_HANDLERS)
    extra = set(_SDK_HANDLERS) - catalog_tools
    if missing or extra:
        raise RuntimeError(f"MCP handler metadata drift: missing={sorted(missing)} extra={sorted(extra)}")
    return tuple(_registration_from_spec(spec) for spec in specs)


def tool_registrations(*, include_direct: bool = True) -> tuple[McpToolRegistration, ...]:
    """Return all tool registrations, with direct exceptions last."""
    direct = DIRECT_TOOL_REGISTRATIONS if include_direct else ()
    return sdk_tool_registrations() + direct


def tools_for_module(module: str, *, include_direct: bool = True) -> tuple[McpToolRegistration, ...]:
    """Return registrations owned by one MCP tool module."""
    return tuple(entry for entry in tool_registrations(include_direct=include_direct) if entry.module == module)


def get_tool_registration(tool_name: str) -> McpToolRegistration:
    """Return registration metadata for an exposed MCP tool name."""
    for entry in tool_registrations():
        if entry.tool_name == tool_name:
            return entry
    raise KeyError(tool_name)


def catalog_tool(mcp: Any, module: str, tool_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorate an SDK-backed MCP tool after validating catalog metadata."""
    entry = get_tool_registration(tool_name)
    if not entry.sdk_backed or entry.module != module:
        raise RuntimeError(f"{tool_name} is not a catalog-backed {module} MCP tool")
    return _tool_decorator(mcp, entry)


def direct_tool(mcp: Any, module: str, tool_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorate an explicit direct MCP/runtime exception."""
    entry = get_tool_registration(tool_name)
    if entry.sdk_backed or entry.module != module:
        raise RuntimeError(f"{tool_name} is not a direct {module} MCP tool")
    return _tool_decorator(mcp, entry)


def _registration_from_spec(spec: OperationSpec) -> McpToolRegistration:
    module, handler_name, summary = _SDK_HANDLERS[spec.mcp_tool or ""]
    return McpToolRegistration(
        tool_name=spec.mcp_tool or "",
        module=module,
        handler_name=handler_name,
        summary=summary,
        operation_name=spec.name,
    )


def _tool_decorator(mcp: Any, entry: McpToolRegistration) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        if func.__name__ != entry.tool_name:
            raise RuntimeError(f"Expected MCP tool function {entry.tool_name}, got {func.__name__}")
        if not (func.__doc__ or "").strip():
            func.__doc__ = entry.summary
        return mcp.tool()(func)

    return decorate
