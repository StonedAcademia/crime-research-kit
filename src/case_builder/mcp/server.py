"""FastMCP server assembly and stdio entry point."""

from __future__ import annotations

from . import prompts, resources, tools_gated, tools_read, tools_write
from .context import ServerContext, default_context

SERVER_INSTRUCTIONS = """CRK case-builder MCP server for public-interest true-crime research.

Tool tiers: read/query tools are always safe; write tools stage drafts under
staging/ only; import_extraction is GATED: it writes canonical records and
must only run with confirm=true after explicit user approval. Exports default
public-safe; include_private output is for internal review and must not be
published. Never infer guilt, membership, or motive from proximity; every
claim needs a traceable source.
"""


def create_server(ctx: ServerContext | None = None):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "The MCP server requires the mcp extra. Install with "
            "`uv pip install -p .venv/bin/python -e '.[mcp]'`."
        ) from exc
    context = ctx or default_context()
    mcp = FastMCP("cr-kit", instructions=SERVER_INSTRUCTIONS)
    tools_read.register(mcp, context)
    tools_write.register(mcp, context)
    tools_gated.register(mcp, context)
    resources.register(mcp, context)
    prompts.register(mcp, context)
    return mcp


def main() -> int:
    create_server().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
