"""Shared operation result type for the ops core."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from ..casefile import CasefileError


@dataclass
class OpResult:
    """Uniform result for every case operation across CLI, graph, and MCP."""

    name: str
    ok: bool = True
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    command: list[str] = field(default_factory=list)
    dry_run: bool = False
    skipped: bool = False
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
