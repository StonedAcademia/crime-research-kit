"""Public-safe-by-default export commands."""

from __future__ import annotations

from crime_research_kit._runtime.adapters.ops.result import OpResult
from crime_research_kit._runtime.adapters.ops.runner import CrkRunner


def export_manim(runner: CrkRunner, case_dir: str, *, include_private: bool = False) -> OpResult:
    return runner.run("export_manim", _args("export-manim", case_dir, include_private))


def export_case_charts(
    runner: CrkRunner,
    case_dir: str,
    *,
    include_private: bool = False,
    out_dir: str | None = None,
) -> OpResult:
    return runner.run("export_case_charts", _args("export-case-charts", case_dir, include_private, out_dir))


def export_analysis_charts(
    runner: CrkRunner,
    case_dir: str,
    *,
    include_private: bool = False,
    out_dir: str | None = None,
    clusters_dir: str | None = None,
) -> OpResult:
    args = _args("export-analysis-charts", case_dir, include_private, out_dir)
    _option(args, "--clusters-dir", clusters_dir)
    return runner.run("export_analysis_charts", args)


def export_people_clusters(
    runner: CrkRunner,
    case_dir: str,
    *,
    include_private: bool = False,
    out_dir: str | None = None,
    charts_dir: str | None = None,
    resolution: float = 1.0,
    seed: int = 7,
    sigma: float | None = None,
) -> OpResult:
    args = _args("export-people-clusters", case_dir, include_private, out_dir)
    _option(args, "--charts-dir", charts_dir)
    args.extend(["--resolution", str(resolution), "--seed", str(seed)])
    if sigma is not None:
        args.extend(["--sigma", str(sigma)])
    return runner.run("export_people_clusters", args)


def export_timeline(
    runner: CrkRunner,
    cases_root: str,
    *,
    include_private: bool = False,
    out_dir: str | None = None,
) -> OpResult:
    return runner.run("export_timeline", _args("export-timeline", cases_root, include_private, out_dir))


def _args(subcommand: str, target: str, include_private: bool, out_dir: str | None = None) -> list[str]:
    args = [subcommand, target]
    _option(args, "--out-dir", out_dir)
    if include_private:
        args.append("--include-private")
    return args


def _option(args: list[str], name: str, value: str | None) -> None:
    if value:
        args.extend([name, value])
