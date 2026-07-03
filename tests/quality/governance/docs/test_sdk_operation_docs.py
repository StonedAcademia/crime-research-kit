from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path

from crime_research_kit.sdk import operations as sdk_operations
from crime_research_kit.sdk.operations import list_operations
from crime_research_kit.sdk.results import OperationResult
from tests.helpers import KIT_ROOT


DOC_ROOT = KIT_ROOT / "docs" / "guides" / "integrations" / "skill-api"
OPERATIONS_INDEX = DOC_ROOT / "operations" / "README.md"
CORE_OPERATIONS = DOC_ROOT / "operations" / "core.md"
HTTP_VERSIONING = DOC_ROOT / "exports" / "http-versioning.md"
OPERATION_HEADING_RE = re.compile(r"^## `([^`]+)`\s*$")


def test_skill_api_operation_reference_matches_sdk_catalog():
    documented = _operation_reference_rows()
    expected = {
        spec.skill_api_name: (spec.name, spec.safety_tier.value, spec.result_model)
        for spec in _skill_api_specs()
    }

    assert documented == expected


def test_skill_api_operation_reference_declares_catalog_drift_gate():
    text = OPERATIONS_INDEX.read_text(encoding="utf-8")

    assert "crime_research_kit.sdk.operations.list_operations()" in text
    assert "test_sdk_operation_docs.py" in text


def test_skill_api_operation_detail_headings_match_sdk_catalog():
    documented = _operation_headings()
    expected = {spec.skill_api_name for spec in _skill_api_specs()}

    assert documented == expected


def test_skill_api_response_envelope_matches_sdk_operation_result():
    documented = _json_block_after(CORE_OPERATIONS, "Common response envelope:")
    expected_fields = list(OperationResult.model_fields)

    assert list(documented) == expected_fields
    assert documented["operation"] == "operationName"
    assert documented["case_ref"] == "data/cases/<case_slug>"


def test_skill_api_http_versioning_routes_match_sdk_catalog():
    documented = _http_mapping_rows()
    expected = _catalog_http_route_rows()

    assert documented == expected


def _skill_api_specs():
    return tuple(spec for spec in list_operations() if spec.skill_api_name)


def _operation_reference_rows() -> dict[str, tuple[str, str, str]]:
    lines = OPERATIONS_INDEX.read_text(encoding="utf-8").splitlines()
    header = "| Skill API operation | SDK operation | Safety tier | Result envelope |"
    start = lines.index(header)
    rows: dict[str, tuple[str, str, str]] = {}

    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        operation, sdk_name, safety_tier, result = [_strip_cell(cell) for cell in line.strip("|").split("|")]
        assert operation not in rows, operation
        rows[operation] = (sdk_name, safety_tier, result)

    return rows


def _operation_headings() -> set[str]:
    headings: set[str] = set()
    for path in DOC_ROOT.rglob("*.md"):
        for line in path.read_text(encoding="utf-8").splitlines():
            match = OPERATION_HEADING_RE.match(line)
            if match:
                headings.add(match.group(1))
    return headings


def _http_mapping_rows() -> dict[str, tuple[str, str]]:
    lines = HTTP_VERSIONING.read_text(encoding="utf-8").splitlines()
    header = "| Method | Path | Operation |"
    start = lines.index(header)
    rows: dict[str, tuple[str, str]] = {}

    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        method, path, operation = [_strip_cell(cell) for cell in line.strip("|").split("|")]
        assert operation not in rows, operation
        rows[operation] = (method, path)

    return rows


def _catalog_http_route_rows() -> dict[str, tuple[str, str]]:
    route_bindings = getattr(sdk_operations, "http_route_bindings", None)
    if route_bindings is not None:
        return _structured_http_route_rows(route_bindings())

    rows: dict[str, tuple[str, str]] = {}
    for spec in list_operations():
        if not spec.http_route:
            continue
        assert spec.skill_api_name, f"{spec.name} defines an HTTP route without a Skill API operation"
        rows[spec.skill_api_name] = _split_http_route(spec.http_route)
    return rows


def _structured_http_route_rows(bindings: Iterable[object] | Mapping[object, object]) -> dict[str, tuple[str, str]]:
    rows: dict[str, tuple[str, str]] = {}
    iterable = bindings.values() if isinstance(bindings, Mapping) else bindings

    for binding in iterable:
        operation = _binding_operation_name(binding)
        assert operation not in rows, operation
        rows[operation] = _binding_route(binding)

    return rows


def _binding_operation_name(binding: object) -> str:
    value = _binding_value(
        binding,
        "skill_api_name",
        "skill_api_operation",
        "operation",
        "operation_name",
        "sdk_operation",
        "name",
    )
    if value is None:
        value = _binding_value(binding, "spec", "operation_spec")

    assert value is not None, f"HTTP binding lacks an operation name: {binding!r}"

    if isinstance(value, str):
        spec = getattr(sdk_operations, "OPERATION_BY_NAME", {}).get(value)
        if spec is not None and spec.skill_api_name:
            return spec.skill_api_name
        return value

    skill_api_name = getattr(value, "skill_api_name", None)
    if skill_api_name:
        return str(skill_api_name)
    return str(value)


def _binding_route(binding: object) -> tuple[str, str]:
    method = _binding_value(binding, "method", "http_method")
    path = _binding_value(binding, "path", "route_path")
    if method and path:
        return str(method), str(path)

    route = _binding_value(binding, "http_route", "route")
    assert route is not None, f"HTTP binding lacks method/path or route text: {binding!r}"
    return _split_http_route(str(route))


def _binding_value(binding: object, *names: str) -> object | None:
    for name in names:
        if isinstance(binding, Mapping):
            value = binding.get(name)
        else:
            value = getattr(binding, name, None)
        if value:
            return value
    return None


def _split_http_route(value: str) -> tuple[str, str]:
    method, path = value.strip().split(" ", maxsplit=1)
    return method, path


def _json_block_after(path: Path, marker: str) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    marker_index = lines.index(marker)
    fence_start = next(index for index in range(marker_index + 1, len(lines)) if lines[index] == "```json")
    fence_end = next(index for index in range(fence_start + 1, len(lines)) if lines[index] == "```")
    return json.loads("\n".join(lines[fence_start + 1 : fence_end]))


def _strip_cell(value: str) -> str:
    return value.strip().strip("`")
