"""Privacy and metadata policy for retrieval documents."""

from __future__ import annotations

from typing import Any


def public_allowed(record: dict[str, Any], *, include_private: bool) -> bool:
    if include_private:
        return True
    return record.get("public_export", True) is not False


def scalar_metadata(value: Any) -> str | int | float | bool | None:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return str(value)


def compact_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool | None]:
    return {key: scalar_metadata(value) for key, value in metadata.items() if value is not None}
