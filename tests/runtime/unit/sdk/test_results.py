import pytest
from pydantic import ValidationError

from crime_research_kit.sdk.errors import CrkInputError
from crime_research_kit.sdk.results import OperationResult, OperationWarning


def test_operation_result_defaults_match_skill_api_envelope():
    result = OperationResult(operation="case.info", case_ref="demo_case")

    assert result.ok is True
    assert result.data == {}
    assert result.errors == []
    assert result.warnings == []
    assert result.created == []
    assert result.updated == []
    assert result.outputs == []
    assert result.counts == {}
    assert result.diagnostics == {}

    payload = result.to_dict(include_empty_diagnostics=False)
    assert list(payload) == [
        "ok",
        "operation",
        "case_ref",
        "data",
        "errors",
        "warnings",
        "created",
        "updated",
        "outputs",
        "counts",
    ]


def test_operation_result_keeps_subprocess_details_in_diagnostics():
    result = OperationResult.failure(
        "ingestUrl",
        "command failed",
        case_ref="demo_case",
        diagnostics={
            "command": ["crk-ledger", "ingest-url"],
            "returncode": 1,
            "stdout": "",
            "stderr": "network unavailable",
        },
    )

    payload = result.to_dict()
    assert "command" not in payload
    assert payload["diagnostics"]["command"] == ["crk-ledger", "ingest-url"]
    assert payload["errors"][0]["message"] == "command failed"


def test_operation_result_coerces_typed_errors_and_warnings():
    error = CrkInputError("Invalid source ID", operation="draftExtraction")
    warning = OperationWarning(code="lead_only", message="Candidate rows are not evidence.")

    result = OperationResult(
        ok=False,
        operation="draftExtraction",
        errors=[error],
        warnings=[warning, "Needs review"],
    )

    assert result.errors[0].code == "invalid_input"
    assert result.errors[0].operation == "draftExtraction"
    assert result.warnings[0].code == "lead_only"
    assert result.warnings[1].message == "Needs review"


def test_operation_result_rejects_legacy_subprocess_top_level_fields():
    with pytest.raises(ValidationError):
        OperationResult(operation="validate", command=["crk-ledger", "validate"])


def test_operation_result_success_helper_populates_mutable_fields_safely():
    first = OperationResult.success("case.info", counts={"sources": 1})
    second = OperationResult.success("case.info")

    first.outputs.append("exports/report.md")

    assert first.counts == {"sources": 1}
    assert second.counts == {}
    assert second.outputs == []
