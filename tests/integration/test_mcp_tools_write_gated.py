from pathlib import Path

from case_builder.mcp import tools_gated, tools_write
from case_builder.mcp.context import ServerContext
from case_builder.ops.runner import TrcrRunner
from tests.helpers import KIT_ROOT


def make_ctx(cases_root: Path) -> ServerContext:
    return ServerContext(
        repo_root=KIT_ROOT,
        cases_root=cases_root,
        runner=TrcrRunner(repo_root=KIT_ROOT, dry_run=True),
    )


def test_save_extraction_packet_stages_json(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)
    packet = {
        "source_id": "SDEMO0001",
        "entities": [{"name": "A Witness", "role": "witness", "source_ids": ["SDEMO0001"]}],
    }

    result = tools_write.save_extraction_packet_tool(
        ctx,
        "synthetic_case",
        "SDEMO0001_extraction.json",
        packet,
    )

    assert result["ok"] is True
    assert (synthetic_case_copy / "staging" / "extractions" / "SDEMO0001_extraction.json").exists()


def test_save_extraction_packet_rejects_guilt_labels(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)
    packet = {"entities": [{"name": "A Person", "role": "suspect"}]}

    result = tools_write.save_extraction_packet_tool(ctx, "synthetic_case", "bad.json", packet)

    assert result["ok"] is False


def test_ingest_url_tool_builds_command(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_write.ingest_url_tool(
        ctx,
        "synthetic_case",
        "https://example.com/story",
        source_type="news_article",
    )

    assert result["command"][2] == "ingest-url"


def test_import_extraction_refuses_without_confirm(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_gated.import_extraction_tool(ctx, "synthetic_case", "p.json")

    assert result["ok"] is False
    assert any("confirm" in error for error in result["errors"])


def test_import_extraction_rejects_path_like_packet_names(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_gated.import_extraction_tool(
        ctx,
        "synthetic_case",
        "../records/claims.jsonl",
        confirm=True,
    )

    assert result["ok"] is False


def test_import_extraction_plans_command_with_confirm(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_gated.import_extraction_tool(ctx, "synthetic_case", "p.json", confirm=True)

    assert result["ok"] is True
    assert result["command"][2] == "import-extraction"
    assert result["command"][4].endswith("staging/extractions/p.json")


def test_exports_echo_privacy_mode(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    public = tools_gated.export_manim_tool(ctx, "synthetic_case")
    internal = tools_gated.export_manim_tool(ctx, "synthetic_case", include_private=True)

    assert "--include-private" not in public["command"]
    assert "excluded" in public["data"]["privacy"]
    assert "--include-private" in internal["command"]
    assert "internal review" in internal["data"]["privacy"]
