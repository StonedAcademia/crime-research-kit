import pytest

from cli import build_parser


def test_plan_parser_accepts_pipeline_flags():
    parser = build_parser()

    args = parser.parse_args(
        [
            "plan",
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
        ]
    )

    assert args.source_url == ["https://a.example"]
    assert args.source_id == ["S0001"]
    assert args.index is True
    assert args.checkpoint is True
    assert args.thread == "t1"


def test_resume_parser_accepts_review_decisions():
    parser = build_parser()

    args = parser.parse_args(
        [
            "resume",
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
        ]
    )

    assert args.command == "resume"
    assert args.approve_packet == ["S1_extraction.json"]
    assert args.reject_packet == ["S2_extraction.json"]
    assert args.approve_export is True


def test_plan_parser_accepts_llm_flag():
    parser = build_parser()

    args = parser.parse_args(["plan", "data/cases/x", "--llm"])

    assert args.llm is True


def test_llm_disabled_state_never_builds_a_model(monkeypatch):
    from pipeline.app import service
    from core.models.state import CaseBuilderState

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
    from pipeline.app.service import run_case_builder
    from core.models.state import CaseBuilderState

    with pytest.raises(RuntimeError):
        run_case_builder(CaseBuilderState(case_dir="data/cases/x"), runner="sequential", checkpoint=True)


def test_service_checkpoint_pause_and_resume(tmp_path):
    pytest.importorskip("langgraph")
    from pipeline.app.service import resume_case_builder, run_case_builder
    from core.models.state import CaseBuilderState

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
