"""Typer commands for ledger exports and reports."""

from __future__ import annotations

import typer

from crime_research_kit._runtime.adapters.interfaces.cli.commands import dispatch
from crime_research_kit._runtime.adapters.ops.evidence.reports import case_outputs, timeline
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command import entry as analysis_charts
from crime_research_kit._runtime.adapters.ops.evidence.reports.case_charts import command as case_charts
from crime_research_kit._runtime.adapters.ops.evidence.reports.clusters import command as clusters

app = typer.Typer(no_args_is_help=True)


@app.command("export-manim", help="Export public-safe Manim-ready CSVs")
def export_manim(
    case_dir: str = typer.Argument(...),
    include_private: bool = typer.Option(False, "--include-private"),
) -> None:
    dispatch(case_outputs.export_manim, case_dir=case_dir, include_private=include_private)


@app.command("export-timeline", help="Export cross-case timeline and claim corroboration CSVs")
def export_timeline(
    cases_root: str = typer.Argument(...),
    out_dir: str | None = typer.Option(None, "--out-dir"),
    include_private: bool = typer.Option(False, "--include-private"),
) -> None:
    dispatch(timeline.export_timeline, cases_root=cases_root, out_dir=out_dir, include_private=include_private)


@app.command("export-case-charts", help="Export people-only graph and subcase timeline chart artifacts")
def export_case_charts(
    case_dir: str = typer.Argument(...),
    out_dir: str | None = typer.Option(None, "--out-dir"),
    include_private: bool = typer.Option(False, "--include-private"),
) -> None:
    dispatch(case_charts.export_case_charts, case_dir=case_dir, out_dir=out_dir, include_private=include_private)


@app.command("export-analysis-charts", help="Export extended analysis chart CSVs and dashboard")
def export_analysis_charts(
    case_dir: str = typer.Argument(...),
    out_dir: str | None = typer.Option(None, "--out-dir"),
    clusters_dir: str | None = typer.Option(None, "--clusters-dir"),
    include_private: bool = typer.Option(False, "--include-private"),
) -> None:
    dispatch(
        analysis_charts.export_analysis_charts,
        case_dir=case_dir,
        out_dir=out_dir,
        clusters_dir=clusters_dir,
        include_private=include_private,
    )


@app.command("export-people-clusters", help="Run evidence-weighted Leiden clustering and graph-kernel/KDE analysis on people graph")
def export_people_clusters(
    case_dir: str = typer.Argument(...),
    out_dir: str | None = typer.Option(None, "--out-dir"),
    charts_dir: str | None = typer.Option(None, "--charts-dir"),
    include_private: bool = typer.Option(False, "--include-private"),
    resolution: float = typer.Option(1.0, "--resolution"),
    seed: int = typer.Option(7, "--seed"),
    sigma: float | None = typer.Option(None, "--sigma"),
) -> None:
    dispatch(
        clusters.export_people_clusters,
        case_dir=case_dir,
        out_dir=out_dir,
        charts_dir=charts_dir,
        include_private=include_private,
        resolution=resolution,
        seed=seed,
        sigma=sigma,
    )


@app.command("report", help="Write Markdown evidence board")
def report(case_dir: str = typer.Argument(...)) -> None:
    dispatch(case_outputs.report, case_dir=case_dir)
