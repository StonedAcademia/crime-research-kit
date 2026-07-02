"""Provider-neutral workflow memory types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class MemoryEntry:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryProvider(Protocol):
    def add(self, entry: MemoryEntry) -> dict[str, Any]:
        """Persist a workflow memory entry."""
