import pytest

from types import SimpleNamespace

from crime_research_kit._runtime.cli import build_click_command


def parse_command(command: str, args: list[str]) -> SimpleNamespace:
    with build_click_command().commands[command].make_context(command, args) as ctx:
        params = {key: list(value) if isinstance(value, tuple) else value for key, value in ctx.params.items()}
        return SimpleNamespace(command=command, **params)


def test_plan_parser_accepts_pipeline_flags():
    args = parse_command("plan", [
        "data/cases/x",
        "--subject",
        "test",
        "--source-url",
        "https://a.example",
        "--source-id",
        "S0001",
        "--index",
        "--checkpoint",
        "--thread",
        "t1",
    ])

    assert args.source_url == ["https://a.example"]
    assert args.source_id == ["S0001"]
    assert args.index is True
    assert args.checkpoint is True
    assert args.thread == "t1"


def test_resume_parser_accepts_review_decisions():
    args = parse_command("resume", [
        "data/cases/x",
        "--thread",
        "t1",
        "--approve-packet",
        "S1_extraction.json",
        "--reject-packet",
        "S2_extraction.json",
        "--reason",
        "insufficient sourcing",
        "--approve-export",
    ])

    assert args.command == "resume"
    assert args.approve_packet == ["S1_extraction.json"]
    assert args.reject_packet == ["S2_extraction.json"]
    assert args.approve_export is True


def test_plan_parser_accepts_llm_flag():
    args = parse_command("plan", ["data/cases/x", "--llm"])

    assert args.llm is True


def test_plan_handler_uses_sdk_workflow(monkeypatch):
    from crime_research_kit._runtime.adapters.interfaces.cli.case_builder import handlers
    from crime_research_kit.sdk import OperationResult
    from crime_research_kit.sdk.workflows import WorkflowClient

    captured = {}

    def fake_plan(self, request):
        captured["request"] = request
        return OperationResult.success("workflows.plan", data={"status": "waiting_for_human_review"})

    monkeypatch.setattr(WorkflowClient, "plan", fake_plan)

    result = handlers.run_plan_command(
        SimpleNamespace(
            case_dir="data/cases/x",
            title="Case",
            subject="subject",
            lane=["legal-court"],
            source_url=["https://example.test"],
            source_id=["S1"],
            index=True,
            thread="sdk-t1",
            llm=True,
            execute=False,
            runner="sequential",
            checkpoint=False,
            settings=SimpleNamespace(model_spec="local-model", qdrant_url="http://qdrant:6333", embed_model="local-embed"),
        )
    )

    assert result == {"status": "waiting_for_human_review"}
    assert captured["request"].case_dir == "data/cases/x"
    assert captured["request"].model_spec == "local-model"
    assert captured["request"].index is True


def test_resume_handler_uses_sdk_workflow(monkeypatch):
    from crime_research_kit._runtime.adapters.interfaces.cli.case_builder import handlers
    from crime_research_kit.sdk import OperationResult
    from crime_research_kit.sdk.workflows import WorkflowClient

    captured = {}

    def fake_resume(self, request):
        captured["request"] = request
        return OperationResult.success("workflows.resume", data={"status": "bundle_exported"})

    monkeypatch.setattr(WorkflowClient, "resume", fake_resume)

    result = handlers.run_resume_command(
        SimpleNamespace(
            case_dir="data/cases/x",
            thread="sdk-t2",
            approve_packet=["S1_extraction.json"],
            reject_packet=["S2_extraction.json"],
            reason="insufficient sourcing",
            approve_export=True,
            execute=False,
            llm=False,
            settings=SimpleNamespace(model_spec="local-model", model_fields_set=set()),
        )
    )

    assert result == {"status": "bundle_exported"}
    assert captured["request"].thread_id == "sdk-t2"
    assert captured["request"].rejected_packets == ["S2_extraction.json"]
    assert captured["request"].reject_reason == "insufficient sourcing"


def test_local_source_handlers_use_sdk_sources(monkeypatch):
    from crime_research_kit._runtime.adapters.interfaces.cli.case_builder import handlers
    from crime_research_kit.sdk import OperationResult
    from crime_research_kit.sdk.sources import CaseSourcesClient

    captured = {}

    def fake_discover(self, **kwargs):
        captured["discover"] = kwargs
        return OperationResult.success("sources.discover", data={"candidates": []})

    def fake_parse(self, source_id, **kwargs):
        captured["parse"] = (source_id, kwargs)
        return OperationResult.success("sources.parse", data={"source_id": source_id})

    monkeypatch.setattr(CaseSourcesClient, "discover", fake_discover)
    monkeypatch.setattr(CaseSourcesClient, "parse", fake_parse)

    discovered = handlers.run_discover_command(
        SimpleNamespace(
            case_dir="data/cases/x",
            query="subject",
            searxng_url=None,
            limit=3,
            out="staging/candidates/sources.json",
            settings=SimpleNamespace(searxng_url="http://searxng:8080"),
        )
    )
    parsed = handlers.run_parse_command(SimpleNamespace(case_dir="data/cases/x", source_id="S1", force=True))

    assert discovered == {"candidates": []}
    assert parsed == {"source_id": "S1"}
    assert captured["discover"]["searxng_url"] == "http://searxng:8080"
    assert captured["parse"] == ("S1", {"force": True})


def test_llm_disabled_state_never_builds_a_model(monkeypatch):
    from crime_research_kit._runtime.pipeline.app import service
    from crime_research_kit._runtime.core.models.state import CaseBuilderState

    def explode():
        raise AssertionError("model factory must not be constructed when llm is disabled")

    monkeypatch.setattr(
        service, "_model_factory", lambda enabled, model_spec=None: explode() if enabled else None
    )

    result = service.run_case_builder(
        CaseBuilderState(case_dir="data/cases/x", subject="s"),
        runner="sequential",
    )

    assert result["status"] == "waiting_for_human_review"


def test_checkpoint_requires_langgraph_runner():
    from crime_research_kit._runtime.pipeline.app.service import run_case_builder
    from crime_research_kit._runtime.core.models.state import CaseBuilderState

    with pytest.raises(RuntimeError):
        run_case_builder(CaseBuilderState(case_dir="data/cases/x"), runner="sequential", checkpoint=True)


def test_service_checkpoint_pause_and_resume(tmp_path):
    pytest.importorskip("langgraph")
    from crime_research_kit._runtime.pipeline.app.service import resume_case_builder, run_case_builder
    from crime_research_kit._runtime.core.models.state import CaseBuilderState

    case_dir = str(tmp_path / "svc_case")
    state = CaseBuilderState(case_dir=case_dir, subject="missing person map", thread_id="svc-t1")

    first = run_case_builder(state, execute=False, runner="langgraph", checkpoint=True)
    assert first["thread_id"] == "svc-t1"
    assert first["paused_before"] == ["packet_review_gate"]

    second = resume_case_builder(case_dir, thread_id="svc-t1", approved_packets=["S1_extraction.json"])
    assert second["paused_before"] == ["export_review_gate"]

    final = resume_case_builder(case_dir, thread_id="svc-t1", export_approved=True)
    assert final["paused_before"] == []
    assert final["status"] == "bundle_exported"
