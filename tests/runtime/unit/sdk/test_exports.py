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


def test_exports_case_visuals_plan_options(synthetic_case_copy: Path):
    case = dry_client_for(synthetic_case_copy).case("synthetic_case")

    visuals = case.exports.case_visuals(out_dir="tmp/visuals")
    internal = case.exports.case_visuals(include_private=True, out_dir="tmp/internal-visuals")

    visual_args = ledger_command_args(visuals.diagnostics["command"])
    internal_args = ledger_command_args(internal.diagnostics["command"])
    assert visuals.operation == "exports.case_visuals"
    assert visual_args[:2] == ["export-case-visuals", str(synthetic_case_copy)]
    assert visual_args[visual_args.index("--out-dir") + 1] == "tmp/visuals"
    assert "--include-private" not in visual_args
    assert internal.operation == "exports.case_visuals"
    assert internal_args[internal_args.index("--out-dir") + 1] == "tmp/internal-visuals"
    assert "--include-private" in internal_args


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
