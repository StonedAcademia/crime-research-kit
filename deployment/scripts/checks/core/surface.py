"""Introspect CLI command surfaces into a comparable dict."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from enum import Enum
from typing import Any


def argparse_surface(parser: argparse.ArgumentParser) -> dict[str, Any]:
    """Return a stable command surface for an argparse parser."""
    surface: dict[str, Any] = {}
    seen_subparsers: dict[int, str] = {}
    subactions = [action for action in parser._actions if isinstance(action, argparse._SubParsersAction)]
    for subaction in subactions:
        for name, subparser in subaction.choices.items():
            parser_id = id(subparser)
            if parser_id in seen_subparsers:
                surface[seen_subparsers[parser_id]]["aliases"].append(name)
                continue
            seen_subparsers[parser_id] = name
            surface[name] = {
                "aliases": [],
                **_argparse_command_surface(subparser),
            }
    return _sorted_surface(surface)


def click_surface(root: Any) -> dict[str, Any]:
    """Return a stable command surface for a click/typer command group."""
    import click

    surface: dict[str, Any] = {}
    seen_commands: dict[int, str] = {}
    for name, command in root.commands.items():
        command_key = _command_key(command)
        if command_key in seen_commands:
            surface[seen_commands[command_key]]["aliases"].append(name)
            continue
        seen_commands[command_key] = name
        args: list[str] = []
        options: dict[str, Any] = {}
        for param in command.params:
            if isinstance(param, click.Argument) or getattr(param, "param_type_name", None) == "argument":
                args.append(param.name)
                continue
            option_names = sorted([*param.opts, *param.secondary_opts])
            key = _primary_option(option_names)
            raw_choices = getattr(param.type, "choices", None)
            choices = sorted(raw_choices) if raw_choices else None
            options[key] = {
                "aliases": option_names,
                "default": _comparable_default(param.default),
                "required": bool(param.required),
                "choices": choices,
                "is_flag": bool(param.is_flag),
            }
        surface[name] = {"aliases": [], "args": args, "options": dict(sorted(options.items()))}
    return _sorted_surface(surface)


def _argparse_command_surface(parser: argparse.ArgumentParser) -> dict[str, Any]:
    args: list[str] = []
    options: dict[str, Any] = {}
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        if not action.option_strings:
            args.append(action.dest)
            continue
        option_names = sorted(action.option_strings)
        key = _primary_option(option_names)
        choices = sorted(action.choices) if action.choices else None
        options[key] = {
            "aliases": option_names,
            "default": _comparable_default(action.default),
            "required": bool(action.required),
            "choices": choices,
            "is_flag": isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)),
        }
    return {"args": args, "options": dict(sorted(options.items()))}


def _primary_option(option_names: Iterable[str]) -> str:
    return max(option_names, key=lambda value: (len(value), value))


def _comparable_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_comparable_default(item) for item in value]
    if isinstance(value, list):
        return [_comparable_default(item) for item in value]
    if isinstance(value, set):
        return sorted(_comparable_default(item) for item in value)
    return value


def _command_key(command: Any) -> int:
    callback = getattr(command, "callback", None)
    wrapped = getattr(callback, "__wrapped__", callback)
    return id(wrapped) if wrapped is not None else id(command)


def _sorted_surface(surface: dict[str, Any]) -> dict[str, Any]:
    for command in surface.values():
        command["aliases"] = sorted(command["aliases"])
    return dict(sorted(surface.items()))
