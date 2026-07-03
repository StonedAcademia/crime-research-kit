"""Ledger CLI executable entry."""

from __future__ import annotations

import click

from crime_research_kit._runtime.core.casefile import CasefileError

from .app import build_click_command


def main(argv: list[str] | None = None) -> int:
    command = build_click_command()
    try:
        command.main(args=argv, standalone_mode=False)
    except CasefileError as exc:
        raise SystemExit(str(exc)) from exc
    except click.exceptions.Abort as exc:
        raise SystemExit(1) from exc
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
    return 0
