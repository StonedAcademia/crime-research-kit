"""Shared operation result type for the ops core."""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field

from core.casefile import CasefileError


class OpResult(BaseModel):
    """Uniform result for every case operation across CLI, graph, and MCP."""

    name: str
    ok: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    command: list[str] = Field(default_factory=list)
    dry_run: bool = False
    skipped: bool = False
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


def local_op(
    name: str,
    func: Callable[..., dict[str, Any]],
    /,
    *args: Any,
    **kwargs: Any,
) -> OpResult:
    """Run a Python-native case operation, mapping CasefileError to a failed result."""
    try:
        data = func(*args, **kwargs)
    except CasefileError as exc:
        return OpResult(name=name, ok=False, errors=[str(exc)])
    return OpResult(name=name, data=data)
