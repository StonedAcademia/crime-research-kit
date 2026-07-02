"""Public-safe-by-default export commands."""

from __future__ import annotations

from .result import OpResult
from .runner import CrkRunner


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
) -> OpResult:
    return runner.run("export_analysis_charts", _args("export-analysis-charts", case_dir, include_private, out_dir))


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
    if out_dir:
        args.extend(["--out-dir", out_dir])
    if include_private:
        args.append("--include-private")
    return args
