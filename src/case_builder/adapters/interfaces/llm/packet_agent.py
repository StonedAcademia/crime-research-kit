"""Bounded packet-filling agent: one structured-output call plus one retry.

Context is bounded by head+tail truncation; selecting chunks via the local
retrieval index is a follow-up once indexed cases are the norm.
"""

from __future__ import annotations

import json
from typing import Any

from case_builder.adapters.ops.safety.policy import apply_automation_defaults, lint_guilt_labels

ASSERTION_RECORD_KEYS = ("claims", "events", "relationships", "event_links", "quotes")
TRUNCATION_MARK = "\n...[truncated]...\n"

PROMPT_TEMPLATE = """You are filling a research extraction packet from one source text.

Rules:
- Output ONLY the completed JSON packet. No prose, no code fences.
- Keep exactly the packet's existing top-level keys. Do not add new ones.
- Every record you add must include "source_ids": ["{source_id}"]. Never cite any other source.
- Record only what the source itself states. Preserve how the source frames it.
- Use neutral role labels (witness, person_mentioned, former_member, official, relative).
  Never label anyone suspect/perpetrator/accomplice/cult member unless the source
  uses that exact wording, and then include "label_source_ids": ["{source_id}"].
- Leave uncertainty visible; do not resolve contradictions.

Packet template:
{packet_json}

Source text:
{source_text}
"""

RETRY_TEMPLATE = """Your previous packet was rejected for these reasons:
{problems}

Fix every problem and output ONLY the corrected JSON packet.

{original_prompt}"""


class PacketAgentError(RuntimeError):
    """Raised when the model cannot produce a valid packet within one retry."""


def fill_packet(
    model: Any,
    packet: dict[str, Any],
    source_text: str,
    *,
    source_id: str,
    max_chars: int = 24000,
) -> dict[str, Any]:
    prompt = PROMPT_TEMPLATE.format(
        source_id=source_id,
        packet_json=json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
        source_text=bounded_context(source_text, max_chars),
    )
    problems: list[str] = []
    for attempt in range(2):
        request = prompt if attempt == 0 else RETRY_TEMPLATE.format(
            problems="\n".join(problems),
            original_prompt=prompt,
        )
        reply = model.invoke(request)
        content = str(getattr(reply, "content", reply))
        try:
            filled = parse_json_response(content)
        except ValueError as exc:
            problems = [str(exc)]
            continue
        problems = validate_filled_packet(packet, filled, source_id)
        if not problems:
            return harden_records(filled)
    raise PacketAgentError("; ".join(problems))


def parse_json_response(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"The response was not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("The response must be a JSON object matching the packet template.")
    return parsed


def validate_filled_packet(
    template: dict[str, Any],
    filled: dict[str, Any],
    source_id: str,
) -> list[str]:
    problems = [f"Unknown top-level key: {key}" for key in filled if key not in template]
    for key, value in filled.items():
        if not isinstance(value, list):
            continue
        for index, record in enumerate(value):
            if isinstance(record, dict) and source_id not in (record.get("source_ids") or []):
                problems.append(f"{key}[{index}] must cite source_ids ['{source_id}']; never invent source IDs")
    problems.extend(f"guilt-label lint: {item}" for item in lint_guilt_labels(filled))
    return problems


def harden_records(filled: dict[str, Any]) -> dict[str, Any]:
    hardened: dict[str, Any] = {}
    for key, value in filled.items():
        if isinstance(value, list) and key in ASSERTION_RECORD_KEYS:
            hardened[key] = [apply_automation_defaults(record) if isinstance(record, dict) else record for record in value]
        elif isinstance(value, list):
            hardened[key] = [{**record, "public_export": False} if isinstance(record, dict) else record for record in value]
        else:
            hardened[key] = value
    return hardened


def bounded_context(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    head = text[: max_chars * 2 // 3]
    tail = text[-(max_chars - len(head)) :]
    return head + TRUNCATION_MARK + tail
