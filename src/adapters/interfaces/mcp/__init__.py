"""MCP server package. The SDK loads lazily in server.py."""

from __future__ import annotations

from .content import prompts, resources
from .tools import gated as tools_gated
from .tools import read as tools_read
from .tools import write as tools_write

__all__ = ["prompts", "resources", "tools_gated", "tools_read", "tools_write"]
