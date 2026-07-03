from __future__ import annotations

import json
import re
from pathlib import Path

from crime_research_kit.sdk.operations import list_operations
from crime_research_kit.sdk.results import OperationResult
from tests.helpers import KIT_ROOT


DOC_ROOT = KIT_ROOT / "docs" / "guides" / "integrations" / "skill-api"
OPERATIONS_INDEX = DOC_ROOT / "operations" / "README.md"
CORE_OPERATIONS = DOC_ROOT / "operations" / "core.md"
OPERATION_HEADING_RE = re.compile(r"^## `([^`]+)`\s*$")


def test_skill_api_operation_reference_matches_sdk_catalog():
    documented = _operation_reference_rows()
    expected = {
        spec.skill_api_name: (spec.name, spec.safety_tier.value, spec.result_model)
        for spec in _skill_api_specs()
    }

    assert documented == expected


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


def _json_block_after(path: Path, marker: str) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    marker_index = lines.index(marker)
    fence_start = next(index for index in range(marker_index + 1, len(lines)) if lines[index] == "```json")
    fence_end = next(index for index in range(fence_start + 1, len(lines)) if lines[index] == "```")
    return json.loads("\n".join(lines[fence_start + 1 : fence_end]))


def _strip_cell(value: str) -> str:
    return value.strip().strip("`")
