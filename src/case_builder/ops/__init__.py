"""Typed operations core shared by the CLI, graph nodes, and future MCP server."""

from __future__ import annotations

from .result import OpResult, local_op
from .runner import TrcrRunner

__all__ = ["OpResult", "TrcrRunner", "local_op"]
