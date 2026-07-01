"""Safety contract enforcement shared by every ops function."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..casefile import ensure_case

ALLOWED_WRITE_DIRS: tuple[str, ...] = ("staging", "exports")
GUILT_LABELS: tuple[str, ...] = (
    "suspect",
    "perpetrator",
    "accomplice",
    "person of interest",
    "cult member",
    "co-conspirator",
)
LABEL_KEYS: tuple[str, ...] = ("role", "label", "entity_role", "relationship_type")
MAX_AUTOMATION_CONFIDENCE = 0.3
DEFAULT_AUTOMATION_CONFIDENCE = 0.2


class PolicyError(RuntimeError):
    """Raised when an operation would violate the safety contract."""


def ensure_staged_write(case_dir: str | Path, target: Path) -> None:
    """Allow automated writes only under staging/ and exports/ inside the case."""
    case = ensure_case(case_dir)
    try:
        relative = target.resolve().relative_to(case)
    except ValueError as exc:
        raise PolicyError(f"Write outside the case workspace is not allowed: {target}") from exc
    if not relative.parts or relative.parts[0] not in ALLOWED_WRITE_DIRS:
        raise PolicyError(
            "Automated writes must stay under "
            f"{'/'.join(ALLOWED_WRITE_DIRS)}; canonical records go through "
            f"import_extraction: {relative.as_posix()}"
        )


def filter_public(records: Iterable[dict[str, Any]], *, include_private: bool = False) -> list[dict[str, Any]]:
    """Drop records explicitly marked public_export=false unless include_private."""
    rows = list(records)
    if include_private:
        return rows
    return [row for row in rows if row.get("public_export") is not False]


def apply_automation_defaults(record: dict[str, Any]) -> dict[str, Any]:
    """Automated records are unverified, low-confidence, and private by default."""
    confidence = record.get("confidence")
    try:
        capped = (
            min(float(confidence), MAX_AUTOMATION_CONFIDENCE)
            if confidence is not None
            else DEFAULT_AUTOMATION_CONFIDENCE
        )
    except (TypeError, ValueError):
        capped = DEFAULT_AUTOMATION_CONFIDENCE
    return {**record, "status": "unverified", "confidence": capped, "public_export": False}


def lint_guilt_labels(packet: Any, path: str = "$") -> list[str]:
    """Flag guilt-implying labels that lack a citing source."""
    problems: list[str] = []
    if isinstance(packet, dict):
        for key, value in packet.items():
            if _is_uncited_guilt_label(packet, key, value):
                problems.append(
                    f"{path}.{key}={value!r} uses a guilt-implying label without "
                    "label_source_ids citing a source that uses this wording"
                )
            problems.extend(lint_guilt_labels(value, f"{path}.{key}"))
    elif isinstance(packet, list):
        for index, item in enumerate(packet):
            problems.extend(lint_guilt_labels(item, f"{path}[{index}]"))
    return problems


def _is_uncited_guilt_label(packet: dict[str, Any], key: str, value: Any) -> bool:
    if key not in LABEL_KEYS or not isinstance(value, str):
        return False
    if not any(label in value.lower() for label in GUILT_LABELS):
        return False
    return not packet.get("label_source_ids")
