from __future__ import annotations

from pathlib import Path

from crime_research_kit.sdk import CrkClient, CrkContext, WorkflowPlanRequest, WorkflowResumeRequest
from crime_research_kit.sdk.errors import DEPENDENCY_MISSING, INVALID_INPUT
from tests.helpers import KIT_ROOT


def client_for(tmp_path: Path | None = None, *, dry_run: bool = False) -> CrkClient:
    cases_root = tmp_path / "cases" if tmp_path else Path("data/cases")
    return CrkClient(CrkContext(repo_root=KIT_ROOT, cases_root=cases_root, dry_run=dry_run))


def test_workflows_plan_runs_sequential_dry_run(tmp_path: Path):
    result = client_for(tmp_path).workflows.plan(
        "example_case",
        title="Example Case",
        subject="Jane Doe missing person last seen near Riverside Park map",
        runner="sequential",
    )

    assert result.ok is True
    assert result.operation == "workflows.plan"
    assert result.case_ref == str(tmp_path / "cases" / "example_case")
    assert result.data["runner"] == "sequential"
    assert result.data["status"] == "waiting_for_human_review"
    assert result.data["review_required"] is True
    assert result.data["lanes"] == ["missing-persons", "geographical-location"]
    assert result.counts["tool_results"] == 2
    assert result.diagnostics["runner"] == "sequential"


def test_workflows_plan_accepts_request_model(tmp_path: Path):
    request = WorkflowPlanRequest(
        case_dir="demo_case",
        subject="public court filing search",
        lanes=("legal-court",),
        source_urls=("https://example.test/source",),
        source_ids=("S1",),
        runner="sequential",
        thread_id="sdk-t1",
    )

    result = client_for(tmp_path).workflows.plan(request)

    assert result.ok is True
    assert result.data["thread_id"] == "sdk-t1"
    assert result.counts["lanes"] == 1
    assert result.counts["source_urls"] == 1
    assert result.counts["source_ids"] == 1


def test_workflows_plan_maps_checkpoint_input_error(tmp_path: Path):
    result = client_for(tmp_path).workflows.plan("demo_case", runner="sequential", checkpoint=True)

    assert result.ok is False
    assert result.operation == "workflows.plan"
    assert result.errors[0].code == INVALID_INPUT


def test_workflows_resume_requires_thread_id(tmp_path: Path):
    result = client_for(tmp_path).workflows.resume("demo_case")

    assert result.ok is False
    assert result.operation == "workflows.resume"
    assert result.errors[0].code == INVALID_INPUT


def test_workflows_resume_maps_missing_agentic_extra(tmp_path: Path, monkeypatch):
    from pipeline.app import service

    def missing_langgraph(*_args, **_kwargs):
        raise RuntimeError("LangGraph is not installed. Install with `pip install -e '.[agentic]'`.")

    monkeypatch.setattr(service, "resume_case_builder", missing_langgraph)

    result = client_for(tmp_path).workflows.resume("demo_case", thread_id="sdk-t1")

    assert result.ok is False
    assert result.errors[0].code == DEPENDENCY_MISSING


def test_workflows_resume_shapes_rejected_packets(tmp_path: Path, monkeypatch):
    from pipeline.app import service

    captured: dict[str, object] = {}

    def fake_resume(case_dir: str, **kwargs):
        captured["case_dir"] = case_dir
        captured.update(kwargs)
        return {"case_dir": case_dir, "thread_id": kwargs["thread_id"], "status": "bundle_exported", "runner": "langgraph"}

    monkeypatch.setattr(service, "resume_case_builder", fake_resume)
    request = WorkflowResumeRequest(
        case_dir="demo_case",
        thread_id="sdk-t2",
        approved_packets=("S1_extraction.json",),
        rejected_packets=("S2_extraction.json",),
        reject_reason="insufficient sourcing",
        export_approved=True,
    )

    result = client_for(tmp_path).workflows.resume(request)

    assert result.ok is True
    assert captured["approved_packets"] == ["S1_extraction.json"]
    assert captured["rejected_packets"] == [{"packet": "S2_extraction.json", "reason": "insufficient sourcing"}]
    assert captured["export_approved"] is True
    assert captured["repo_root"] == KIT_ROOT
    assert result.diagnostics["thread_id"] == "sdk-t2"
