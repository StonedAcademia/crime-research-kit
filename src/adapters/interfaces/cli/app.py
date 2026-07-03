"""crk-ledger Typer application."""

from __future__ import annotations

import click
import typer
import typer.main

from adapters.interfaces.cli.commands import casework, planning, quality, reports

app = typer.Typer(help="True Crime / Cult-Origin Research CLI", no_args_is_help=True)
for group in (casework, planning, quality, reports):
    for command in group.app.registered_commands:
        app.registered_commands.append(command)


def build_click_command() -> click.Command:
    return typer.main.get_command(app)
