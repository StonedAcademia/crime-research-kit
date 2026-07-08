"""Typer commands for ledger exports and reports."""

from __future__ import annotations

import typer

from crime_research_kit._runtime.adapters.interfaces.cli.commands import dispatch
from crime_research_kit._runtime.adapters.ops.evidence.reports import case_outputs, timeline
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages import visuals

app = typer.Typer(no_args_is_help=True)


@app.command("export-timeline", help="Export cross-case timeline and claim corroboration CSVs")
def export_timeline(
    cases_root: str = typer.Argument(...),
    out_dir: str | None = typer.Option(None, "--out-dir"),
    include_private: bool = typer.Option(False, "--include-private"),
) -> None:
    dispatch(timeline.export_timeline, cases_root=cases_root, out_dir=out_dir, include_private=include_private)


@app.command("export-case-visuals", help="Export a curated deck, visual consoles, and audit CSVs")
def export_case_visuals(
    case_dir: str = typer.Argument(...),
    out_dir: str | None = typer.Option(None, "--out-dir"),
    include_private: bool = typer.Option(False, "--include-private"),
) -> None:
    dispatch(visuals.export_case_visuals, case_dir=case_dir, out_dir=out_dir, include_private=include_private)


@app.command("report", help="Write Markdown evidence board")
def report(case_dir: str = typer.Argument(...)) -> None:
    dispatch(case_outputs.report, case_dir=case_dir)
