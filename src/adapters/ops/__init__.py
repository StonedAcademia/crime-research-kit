"""Typed operations core shared by the CLI, graph nodes, and future MCP server."""

from __future__ import annotations

from .casework import case, extraction, sources
from .evidence import exports, query, review
from .result import OpResult, local_op
from .runner import CrkRunner

__all__ = [
    "CrkRunner",
    "OpResult",
    "case",
    "exports",
    "extraction",
    "local_op",
    "query",
    "review",
    "sources",
]
