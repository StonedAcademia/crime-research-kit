"""Shared helpers for ledger Typer command wrappers."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from enum import Enum
from typing import Any, Callable


def dispatch(handler: Callable[[argparse.Namespace], Any], **values: Any) -> None:
    handler(argparse.Namespace(**values))


def choice_enum(name: str, values: Iterable[str]) -> type[Enum]:
    return Enum(name, {_member_name(value): value for value in values}, type=str)


def enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def enum_values(values: Iterable[Any]) -> list[Any]:
    return [enum_value(value) for value in values]


def _member_name(value: str) -> str:
    return value.replace("-", "_").replace(".", "_").upper()
