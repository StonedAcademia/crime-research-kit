import pytest

from core.casefile import CasefileError
from adapters.ops.result import OpResult, local_op


def test_op_result_defaults_and_dict_roundtrip():
    result = OpResult(name="validate")

    assert result.ok is True
    assert result.errors == []
    assert result.warnings == []
    assert result.command == []
    payload = result.to_dict()
    assert payload["name"] == "validate"
    assert payload["dry_run"] is False
    assert payload["skipped"] is False


def test_local_op_wraps_return_value_as_data():
    result = local_op("demo", lambda value: {"answer": value}, 42)

    assert result.ok is True
    assert result.data == {"answer": 42}


def test_local_op_converts_casefile_error_to_failure():
    def boom() -> dict:
        raise CasefileError("not a case")

    result = local_op("demo", boom)

    assert result.ok is False
    assert result.errors == ["not a case"]


def test_local_op_lets_unexpected_errors_propagate():
    def boom() -> dict:
        raise ValueError("bug")

    with pytest.raises(ValueError):
        local_op("demo", boom)
