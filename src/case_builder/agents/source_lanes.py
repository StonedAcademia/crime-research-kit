"""Source-lane routing policy for the initial case-building agent."""

from __future__ import annotations

from collections.abc import Sequence

from ..lanes import registry as lane_registry

FALLBACK_LANES = lane_registry.fallback_source_lanes()
LANE_TRIGGERS: dict[str, tuple[str, ...]] = lane_registry.lane_triggers()



def infer_source_lanes(subject: str | None, explicit_lanes: Sequence[str] | None = None) -> list[str]:
    """Infer conservative source-planning lanes from the seed subject."""
    return lane_registry.infer_lanes(subject, explicit_lanes)
