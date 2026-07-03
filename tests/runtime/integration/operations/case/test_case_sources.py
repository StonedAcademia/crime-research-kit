from pathlib import Path

from crime_research_kit._runtime.adapters.ops import case as case_ops
from crime_research_kit._runtime.adapters.ops import sources as source_ops
from crime_research_kit._runtime.adapters.ops.runner import CrkRunner
from tests.helpers import KIT_ROOT, ledger_command_args, ledger_subcommand

REPO_ROOT = KIT_ROOT


def dry_runner() -> CrkRunner:
    return CrkRunner(repo_root=REPO_ROOT, dry_run=True)


def test_init_case_skips_existing_case(synthetic_case_copy):
    result = case_ops.init_case(dry_runner(), str(synthetic_case_copy), "Synthetic Case")

    assert result.skipped is True
    assert result.name == "init_case"


def test_init_case_plans_command_for_new_case(tmp_path):
    result = case_ops.init_case(dry_runner(), str(tmp_path / "new_case"), None)

    assert result.skipped is False
    assert result.dry_run is True
    assert "init-case" in result.command
    assert "--title" in result.command


def test_case_info_counts_records(synthetic_case_copy):
    result = case_ops.case_info(str(synthetic_case_copy))

    assert result.ok is True
    assert result.data["case_id"] == "synthetic_case"
    assert result.data["record_counts"]["sources"] >= 1
    assert result.data["record_counts"]["claims"] >= 1


def test_case_info_fails_on_non_case(tmp_path):
    result = case_ops.case_info(str(tmp_path))

    assert result.ok is False
    assert result.errors


def test_validate_and_report_plan_commands(synthetic_case_copy):
    runner = dry_runner()

    validate = case_ops.validate(runner, str(synthetic_case_copy))
    report = case_ops.report(runner, str(synthetic_case_copy))

    assert ledger_subcommand(validate.command) == "validate"
    assert ledger_subcommand(report.command) == "report"


def test_plan_public_records_repeats_lane_flags():
    result = source_ops.plan_public_records(
        dry_runner(),
        "data/cases/x",
        "Jane Doe",
        ["legal-court", "missing-persons"],
    )

    assert ledger_subcommand(result.command) == "plan-public-records"
    assert result.command.count("--lane") == 2
    assert "legal-court" in result.command
    assert "missing-persons" in result.command


def test_add_source_builds_optional_flags():
    result = source_ops.add_source(
        dry_runner(),
        "data/cases/x",
        title="A Story",
        url="https://example.com/story",
        source_type="news_article",
        reliability_grade="B",
        public_export=False,
    )

    command = result.command
    assert ledger_subcommand(command) == "add-source"
    assert command[command.index("--title") + 1] == "A Story"
    assert command[command.index("--url") + 1] == "https://example.com/story"
    assert command[command.index("--reliability-grade") + 1] == "B"
    assert "--no-public-export" in command


def test_ingest_url_places_url_positionally():
    result = source_ops.ingest_url(
        dry_runner(),
        "data/cases/x",
        "https://example.com/story",
        source_type="news_article",
    )

    assert ledger_command_args(result.command)[:3] == ["ingest-url", "data/cases/x", "https://example.com/story"]
    assert "--source-type" in result.command


def test_preserve_source_plans_command():
    result = source_ops.preserve_source(
        dry_runner(),
        "data/cases/x",
        "S0001",
        archive_url="https://archive.org/x",
    )

    assert ledger_command_args(result.command)[:3] == ["preserve-source", "data/cases/x", "S0001"]
    assert "--archive-url" in result.command


def test_parse_source_wraps_casefile_error(tmp_path):
    result = source_ops.parse_source(str(tmp_path / "not_a_case"), "S0001")

    assert result.ok is False
    assert result.errors
