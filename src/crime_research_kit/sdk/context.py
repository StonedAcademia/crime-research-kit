"""Conservative context object for SDK callers."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from os import PathLike
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

PathValue = str | PathLike[str] | Path


def _coerce_path(value: PathValue | None) -> Path | None:
    if value is None:
        return None
    return value if isinstance(value, Path) else Path(value)


@dataclass(frozen=True, slots=True)
class CrkContext:
    """Lightweight SDK context without binding to runtime implementation modules."""

    case_dir: Path | None = None
    workspace_dir: Path | None = None
    dry_run: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_dir", _coerce_path(self.case_dir))
        object.__setattr__(self, "workspace_dir", _coerce_path(self.workspace_dir))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def with_case_dir(self, case_dir: PathValue | None) -> "CrkContext":
        """Return a copy with a different case directory."""
        return replace(self, case_dir=_coerce_path(case_dir))

    def with_workspace_dir(self, workspace_dir: PathValue | None) -> "CrkContext":
        """Return a copy with a different workspace directory."""
        return replace(self, workspace_dir=_coerce_path(workspace_dir))


__all__ = ["CrkContext"]
