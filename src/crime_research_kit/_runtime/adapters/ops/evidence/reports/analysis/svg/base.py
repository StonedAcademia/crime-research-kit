"""Shared SVG primitives for analysis charts."""

from __future__ import annotations

import math
import re
from typing import Any

PALETTE = {
    "verified": "#1f7a4f",
    "corroborated": "#2b6cb0",
    "single_source": "#b7791f",
    "unverified": "#a63a3a",
    "disputed": "#7f1d1d",
    "internal_only": "#6b7280",
    "lead_or_disputed": "#a63a3a",
    "source_note_required": "#b7791f",
    "public_ready": "#1f7a4f",
    "usable_with_context": "#2b6cb0",
    "needs_privacy_review": "#7c3aed",
    "A": "#1f7a4f",
    "B": "#2b6cb0",
    "C": "#b7791f",
    "D": "#a63a3a",
    "X": "#2f3742",
}

CHART_COLORS = ["#2b6cb0", "#1f7a4f", "#b7791f", "#7c3aed", "#a63a3a", "#0f766e", "#4b5563", "#c2410c"]


def color_for(value: Any, fallback_index: int = 0) -> str:
    key = str(value or "")
    return PALETTE.get(key, CHART_COLORS[fallback_index % len(CHART_COLORS)])


def short_label(value: Any, max_len: int = 26) -> str:
    text = str(value or "")
    return text if len(text) <= max_len else text[: max_len - 1] + "..."


def parse_year(value: Any) -> int | None:
    match = re.match(r"^(\d{4})", str(value or ""))
    if match:
        return int(match.group(1))
    return None


def pie_path(cx: float, cy: float, radius: float, start: float, end: float) -> str:
    start_x = cx + radius * math.cos(start)
    start_y = cy + radius * math.sin(start)
    end_x = cx + radius * math.cos(end)
    end_y = cy + radius * math.sin(end)
    large = 1 if end - start > math.pi else 0
    return f"M {cx} {cy} L {start_x:.2f} {start_y:.2f} A {radius} {radius} 0 {large} 1 {end_x:.2f} {end_y:.2f} Z"
