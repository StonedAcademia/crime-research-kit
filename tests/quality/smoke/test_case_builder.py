from crime_research_kit._runtime.core.models.state import CaseBuilderState
from crime_research_kit._runtime.pipeline.app.service import run_case_builder


def test_case_builder_dry_run_infers_missing_and_geographical_lanes():
    result = run_case_builder(
        CaseBuilderState(
            case_dir="data/cases/example_case",
            title="Example Case",
            subject="Jane Doe missing person last seen near Riverside Park map",
        ),
        execute=False,
        runner="sequential",
    )

    assert result["runner"] == "sequential"
    assert result["status"] == "waiting_for_human_review"
    assert result["review_required"] is True
    assert result["lanes"] == ["missing-persons", "geographical-location"]
    assert [item["name"] for item in result["tool_results"]] == ["init_case", "plan_public_records"]
    assert all(item["dry_run"] for item in result["tool_results"])
