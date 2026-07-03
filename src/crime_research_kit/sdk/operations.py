"""Operation metadata placeholders for the public SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class SafetyTier(str, Enum):
    """Safety tier assigned to SDK operation specifications."""

    READ = "read"
    STAGED_WRITE = "staged_write"
    CANONICAL_GATED = "canonical_gated"
    PUBLIC_EXPORT = "public_export"
    INTERNAL_SERVICE = "internal_service"


@dataclass(frozen=True, slots=True)
class OperationSpec:
    """Public metadata for an SDK operation before wrappers are promoted."""

    name: str
    domain: str = ""
    safety_tier: SafetyTier = SafetyTier.READ
    summary: str = ""
    requires_case: bool = True
    side_effects: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    cli_command: str | None = None
    mcp_tool: str | None = None
    http_route: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "safety_tier", SafetyTier(self.safety_tier))
        object.__setattr__(self, "side_effects", tuple(self.side_effects))
        object.__setattr__(self, "tags", tuple(self.tags))

    @classmethod
    def from_tags(
        cls,
        name: str,
        *,
        summary: str = "",
        requires_case: bool = True,
        tags: Iterable[str] = (),
    ) -> "OperationSpec":
        """Build an operation spec from any iterable of tags."""
        return cls(name=name, summary=summary, requires_case=requires_case, tags=tuple(tags))


OPERATION_SPECS: tuple[OperationSpec, ...] = ()


def list_operations() -> tuple[OperationSpec, ...]:
    """Return the currently promoted SDK operation specifications."""
    return OPERATION_SPECS


__all__ = ["OPERATION_SPECS", "OperationSpec", "SafetyTier", "list_operations"]
