import json
from pathlib import Path

from adapters.interfaces.mcp import tools_read
from adapters.interfaces.mcp.context import ServerContext
from adapters.ops.runner import CrkRunner
from tests.helpers import KIT_ROOT, ledger_subcommand


def make_ctx(cases_root: Path, dry_run: bool = True) -> ServerContext:
    return ServerContext(
        repo_root=KIT_ROOT,
        cases_root=cases_root,
        runner=CrkRunner(repo_root=KIT_ROOT, dry_run=dry_run),
    )


def test_case_info_tool_returns_counts(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_read.case_info_tool(ctx, "synthetic_case")

    assert result["ok"] is True
    assert result["data"]["record_counts"]["sources"] >= 1


def test_case_info_tool_reports_unknown_case_as_error_dict(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_read.case_info_tool(ctx, "nope")

    assert result["ok"] is False
    assert "Unknown case" in result["errors"][0]


def test_list_cases_tool(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    assert tools_read.list_cases_tool(ctx) == {"ok": True, "cases": ["synthetic_case"]}


def test_get_records_tool_filters_private_and_truncates(synthetic_case_copy):
    claims = synthetic_case_copy / "records" / "claims.jsonl"
    private_row = {
        "claim_id": "CPRIV",
        "claim": "private",
        "source_ids": ["SDEMO0001"],
        "public_export": False,
    }
    claims.write_text(
        claims.read_text(encoding="utf-8") + json.dumps(private_row) + "\n",
        encoding="utf-8",
    )
    ctx = make_ctx(synthetic_case_copy.parent)

    public = tools_read.get_records_tool(ctx, "synthetic_case", "claims")
    limited = tools_read.get_records_tool(
        ctx,
        "synthetic_case",
        "claims",
        include_private=True,
        limit=1,
    )

    assert all(row.get("claim_id") != "CPRIV" for row in public["data"]["records"])
    assert len(limited["data"]["records"]) == 1
    assert limited["data"]["truncated"] is True


def test_run_report_tool_plans_report_command(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_read.run_report_tool(ctx, "synthetic_case")

    assert ledger_subcommand(result["command"]) == "report"


def test_query_case_tool_degrades_to_error_dict(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_read.query_case_tool(ctx, "synthetic_case", "what claims lack spans?")

    assert isinstance(result, dict)
    assert "ok" in result


def test_records_resource_is_public_safe_jsonl(synthetic_case_copy):
    import json as json_module

    from adapters.interfaces.mcp import resources

    claims = synthetic_case_copy / "records" / "claims.jsonl"
    private_row = {
        "claim_id": "CPRIV2",
        "claim": "private",
        "source_ids": ["SDEMO0001"],
        "public_export": False,
    }
    claims.write_text(
        claims.read_text(encoding="utf-8") + json_module.dumps(private_row) + "\n",
        encoding="utf-8",
    )
    ctx = make_ctx(synthetic_case_copy.parent)

    text = resources.records_resource(ctx, "synthetic_case", "claims")

    assert "CPRIV2" not in text
    assert text.strip()


def test_reference_resource_allow_list(synthetic_case_copy):
    import pytest

    from adapters.interfaces.mcp import resources

    ctx = make_ctx(synthetic_case_copy.parent)

    vocab = resources.reference_resource(ctx, "controlled_vocabularies")
    assert vocab.strip()

    with pytest.raises(ValueError):
        resources.reference_resource(ctx, "../SKILL")


def test_prompts_cover_safety_workflow():
    from adapters.interfaces.mcp import prompts

    assert "review" in prompts.REVIEW_PACKET.lower()
    assert "confirm" in prompts.REVIEW_PACKET.lower()
    assert "privacy" in prompts.PUBLIC_READINESS.lower()
