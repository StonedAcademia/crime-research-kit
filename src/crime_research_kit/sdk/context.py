"""Immutable context object for SDK callers."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from os import PathLike
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

PathValue = str | PathLike[str] | Path


class TransportMode(str, Enum):
    """Runtime transport selected by SDK clients."""

    AUTO = "auto"
    DIRECT = "direct"
    SUBPROCESS = "subprocess"


def _coerce_path(value: PathValue | None) -> Path | None:
    if value is None:
        return None
    return value if isinstance(value, Path) else Path(value)


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True)
class CrkContext:
    """Process-boundary settings for SDK clients.

    The context owns caller-visible roots, privacy defaults, transport mode, and
    already-resolved settings without importing runtime implementation modules.
    """

    repo_root: Path | None = None
    cases_root: Path | None = Path("data/cases")
    case_dir: Path | None = None
    workspace_dir: Path | None = None
    include_private: bool = False
    dry_run: bool = False
    transport: TransportMode = TransportMode.AUTO
    settings: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "repo_root", _coerce_path(self.repo_root))
        object.__setattr__(self, "cases_root", _coerce_path(self.cases_root))
        object.__setattr__(self, "case_dir", _coerce_path(self.case_dir))
        object.__setattr__(self, "workspace_dir", _coerce_path(self.workspace_dir))
        object.__setattr__(self, "transport", TransportMode(self.transport))
        object.__setattr__(self, "settings", _freeze_mapping(self.settings))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    def resolve_case_ref(self, case_ref: PathValue | None = None) -> Path | None:
        """Resolve a case slug or path against the configured cases root."""
        value = _coerce_path(case_ref) or self.case_dir
        if value is None:
            return None
        if value.is_absolute() or len(value.parts) > 1:
            return value
        root = self.cases_root or Path("data/cases")
        return root / value

    def with_case_dir(self, case_dir: PathValue | None) -> "CrkContext":
        """Return a copy with a different case directory."""
        return replace(self, case_dir=_coerce_path(case_dir))

    def with_workspace_dir(self, workspace_dir: PathValue | None) -> "CrkContext":
        """Return a copy with a different workspace directory."""
        return replace(self, workspace_dir=_coerce_path(workspace_dir))

    def with_privacy(self, *, include_private: bool) -> "CrkContext":
        """Return a copy with a different privacy default."""
        return replace(self, include_private=include_private)

    def with_transport(self, transport: TransportMode | str) -> "CrkContext":
        """Return a copy with a different transport mode."""
        return replace(self, transport=TransportMode(transport))

    def with_settings(self, **settings: Any) -> "CrkContext":
        """Return a copy with merged resolved settings."""
        return replace(self, settings={**self.settings, **settings})


__all__ = ["CrkContext", "TransportMode"]
