"""Command-line entrypoint for the CRK case-builder agent app."""

from __future__ import annotations

from crime_research_kit._runtime.adapters.interfaces.cli.case_builder import app, build_click_command, main

__all__ = ["app", "build_click_command", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
