"""Layered graph data-product builders."""

from __future__ import annotations

from typing import Any

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.layered.base import build_layered_base
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.builders.layered.v2 import build_layered_v2


def build_layered_graphs(ctx: AnalysisContext) -> dict[str, list[dict[str, Any]]]:
    base = build_layered_base(ctx)
    v2 = build_layered_v2(ctx, base["layered_nodes"], base["layered_edges"])
    return {**base, **v2}
