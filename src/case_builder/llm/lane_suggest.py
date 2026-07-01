"""Optional LLM lane suggestions: recorded with rationale, never auto-applied."""

from __future__ import annotations

import json
from typing import Any, Sequence

from ..agents.source_lanes import LANE_TRIGGERS

PROMPT_TEMPLATE = """Given this research subject, suggest additional public-record
source lanes worth planning. Choose only from this list:
{lanes}

Already selected: {current}

Subject: {subject}

Output ONLY a JSON array of objects: [{{"lane": "<name>", "rationale": "<one sentence>"}}]
Suggest at most 3. Output [] if nothing else applies.
"""


def suggest_lanes(
    model: Any,
    subject: str,
    current_lanes: Sequence[str],
) -> list[dict[str, str]]:
    prompt = PROMPT_TEMPLATE.format(
        lanes=", ".join(sorted(LANE_TRIGGERS)),
        current=", ".join(current_lanes) or "none",
        subject=subject,
    )
    reply = model.invoke(prompt)
    content = str(getattr(reply, "content", reply)).strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    suggestions: list[dict[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        lane = item.get("lane")
        if lane in LANE_TRIGGERS and lane not in current_lanes:
            suggestions.append({"lane": str(lane), "rationale": str(item.get("rationale") or "")})
    return suggestions
