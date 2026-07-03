from pathlib import Path

from crime_research_kit._runtime.adapters.interfaces.mcp import tools_gated, tools_write
from crime_research_kit._runtime.adapters.interfaces.mcp.context import ServerContext
from crime_research_kit._runtime.adapters.ops.runner import CrkRunner
from crime_research_kit._runtime.core.config import CrkSettings
from crime_research_kit.sdk.results import OperationResult
from tests.helpers import KIT_ROOT, ledger_command_args, ledger_subcommand


def make_ctx(cases_root: Path) -> ServerContext:
    return ServerContext(
        repo_root=KIT_ROOT,
        cases_root=cases_root,
        runner=CrkRunner(repo_root=KIT_ROOT, dry_run=True),
        settings=CrkSettings(),
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

    assert ledger_subcommand(result["command"]) == "ingest-url"


def test_ingest_url_tool_routes_through_sdk(monkeypatch, synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)
    calls = {}

    class Sources:
        def ingest_url(
            self,
            url: str,
            *,
            title: str | None,
            source_type: str | None,
            reliability_grade: str | None,
        ) -> OperationResult:
            calls["args"] = (url, title, source_type, reliability_grade)
            return OperationResult.success(
                "sources.ingest_url",
                diagnostics={"command": ["crk-ledger", "ingest-url", url]},
            )

    class Case:
        sources = Sources()

    def fake_sdk_case(_ctx: ServerContext, case: str) -> Case:
        calls["case"] = case
        return Case()

    monkeypatch.setattr(tools_write, "sdk_case", fake_sdk_case)

    result = tools_write.ingest_url_tool(
        ctx,
        "synthetic_case",
        "https://example.com/story",
        title="Story",
        source_type="news_article",
        reliability_grade="B",
    )

    assert calls == {
        "case": "synthetic_case",
        "args": ("https://example.com/story", "Story", "news_article", "B"),
    }
    assert result["operation"] == "sources.ingest_url"
    assert result["command"] == ["crk-ledger", "ingest-url", "https://example.com/story"]


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
    assert ledger_subcommand(result["command"]) == "import-extraction"
    assert ledger_command_args(result["command"])[2].endswith("staging/extractions/p.json")


def test_exports_echo_privacy_mode(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    public = tools_gated.export_manim_tool(ctx, "synthetic_case")
    internal = tools_gated.export_manim_tool(ctx, "synthetic_case", include_private=True)

    assert "--include-private" not in public["command"]
    assert "excluded" in public["data"]["privacy"]
    assert "--include-private" in internal["command"]
    assert "internal review" in internal["data"]["privacy"]


def test_export_manim_tool_routes_through_sdk_and_keeps_privacy_note(monkeypatch, synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)
    calls = {}

    class Exports:
        def manim(self, *, include_private: bool) -> OperationResult:
            calls["include_private"] = include_private
            return OperationResult.success(
                "exports.manim",
                data={"privacy": {"include_private": include_private, "note": "sdk note"}},
                diagnostics={"command": ["crk-ledger", "export-manim", "--include-private"]},
            )

    class Case:
        exports = Exports()

    def fake_sdk_case(_ctx: ServerContext, case: str) -> Case:
        calls["case"] = case
        return Case()

    monkeypatch.setattr(tools_gated, "sdk_case", fake_sdk_case)

    result = tools_gated.export_manim_tool(ctx, "synthetic_case", include_private=True)

    assert calls == {"case": "synthetic_case", "include_private": True}
    assert result["operation"] == "exports.manim"
    assert result["command"] == ["crk-ledger", "export-manim", "--include-private"]
    assert "internal review" in result["data"]["privacy"]


def test_link_names_tool_routes_through_sdk(monkeypatch, synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)
    calls = {}

    class Names:
        def link(self, *, names: list[str]) -> OperationResult:
            calls["names"] = names
            return OperationResult.success("names.link", diagnostics={"command": ["crk-ledger", "link-names"]})

    class Case:
        names = Names()

    def fake_sdk_case(_ctx: ServerContext, case: str) -> Case:
        calls["case"] = case
        return Case()

    monkeypatch.setattr(tools_write, "sdk_case", fake_sdk_case)

    result = tools_write.link_names_tool(ctx, "synthetic_case", ["Jane Doe"])

    assert calls == {"case": "synthetic_case", "names": ["Jane Doe"]}
    assert result["name"] == "link_names"
    assert result["operation"] == "names.link"


def test_plan_public_records_tool_routes_through_sdk(monkeypatch, synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)
    calls = {}

    class Records:
        def plan_public_records(self, subject: str, *, lanes: list[str]) -> OperationResult:
            calls["args"] = (subject, lanes)
            return OperationResult.success(
                "records.plan_public_records",
                diagnostics={"command": ["crk-ledger", "plan-public-records"]},
            )

    class Case:
        records = Records()

    def fake_sdk_case(_ctx: ServerContext, case: str) -> Case:
        calls["case"] = case
        return Case()

    monkeypatch.setattr(tools_write, "sdk_case", fake_sdk_case)

    result = tools_write.plan_public_records_tool(ctx, "synthetic_case", "Jane Doe", ["courts"])

    assert calls == {"case": "synthetic_case", "args": ("Jane Doe", ["courts"])}
    assert result["name"] == "plan_public_records"
    assert result["operation"] == "records.plan_public_records"
