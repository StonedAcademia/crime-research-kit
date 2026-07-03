from __future__ import annotations

from pathlib import Path

from crime_research_kit.sdk import CrkClient, CrkContext
from tests.helpers import KIT_ROOT, ledger_command_args, ledger_subcommand


def dry_client_for(case_dir: Path) -> CrkClient:
    return CrkClient(CrkContext(repo_root=KIT_ROOT, cases_root=case_dir.parent, dry_run=True))


def test_exports_manim_public_safe_by_default(synthetic_case_copy: Path):
    result = dry_client_for(synthetic_case_copy).case("synthetic_case").exports.manim()

    args = ledger_command_args(result.diagnostics["command"])
    assert result.ok is True
    assert result.operation == "exports.manim"
    assert args[:2] == ["export-manim", str(synthetic_case_copy)]
    assert "--include-private" not in args
    assert result.data["privacy"]["include_private"] is False
    assert "public-safe" in result.data["privacy"]["note"]


def test_exports_use_case_privacy_default(synthetic_case_copy: Path):
    case = dry_client_for(synthetic_case_copy).case("synthetic_case").with_privacy(include_private=True)

    result = case.exports.manim()

    args = ledger_command_args(result.diagnostics["command"])
    assert "--include-private" in args
    assert result.data["privacy"]["include_private"] is True
    assert "internal review" in result.data["privacy"]["note"]


def test_exports_case_and_analysis_charts_plan_options(synthetic_case_copy: Path):
    case = dry_client_for(synthetic_case_copy).case("synthetic_case")

    charts = case.exports.case_charts(out_dir="tmp/charts")
    analysis = case.exports.analysis_charts(include_private=True, out_dir="tmp/analysis", clusters_dir="tmp/clusters")

    chart_args = ledger_command_args(charts.diagnostics["command"])
    analysis_args = ledger_command_args(analysis.diagnostics["command"])
    assert charts.operation == "exports.case_charts"
    assert chart_args[:2] == ["export-case-charts", str(synthetic_case_copy)]
    assert chart_args[chart_args.index("--out-dir") + 1] == "tmp/charts"
    assert analysis.operation == "exports.analysis_charts"
    assert analysis_args[analysis_args.index("--out-dir") + 1] == "tmp/analysis"
    assert analysis_args[analysis_args.index("--clusters-dir") + 1] == "tmp/clusters"
    assert "--include-private" in analysis_args


def test_exports_people_clusters_plan_optional_parameters(synthetic_case_copy: Path):
    result = dry_client_for(synthetic_case_copy).case("synthetic_case").exports.people_clusters(
        out_dir="tmp/clusters",
        charts_dir="tmp/charts",
        resolution=1.25,
        seed=11,
        sigma=0.75,
    )

    args = ledger_command_args(result.diagnostics["command"])
    assert result.operation == "exports.people_clusters"
    assert args[:2] == ["export-people-clusters", str(synthetic_case_copy)]
    assert args[args.index("--out-dir") + 1] == "tmp/clusters"
    assert args[args.index("--charts-dir") + 1] == "tmp/charts"
    assert args[args.index("--resolution") + 1] == "1.25"
    assert args[args.index("--seed") + 1] == "11"
    assert args[args.index("--sigma") + 1] == "0.75"


def test_top_level_exports_timeline_uses_cases_root_and_privacy(synthetic_case_copy: Path):
    client = dry_client_for(synthetic_case_copy).with_context(
        CrkContext(repo_root=KIT_ROOT, cases_root=synthetic_case_copy.parent, dry_run=True, include_private=True)
    )

    result = client.exports.timeline(out_dir="tmp/timeline")

    args = ledger_command_args(result.diagnostics["command"])
    assert result.operation == "exports.timeline"
    assert ledger_subcommand(result.diagnostics["command"]) == "export-timeline"
    assert args[1] == str(synthetic_case_copy.parent)
    assert args[args.index("--out-dir") + 1] == "tmp/timeline"
    assert "--include-private" in args
