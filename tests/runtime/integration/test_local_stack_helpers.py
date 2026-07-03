from pathlib import Path

import pytest

from tests import helpers
from crime_research_kit._runtime.core.casefile import find_source


def test_register_pdf_source_copies_and_records(synthetic_case_copy: Path):
    rel = helpers.register_pdf_source(synthetic_case_copy, "SFIX0001", helpers.DOCS_FIXTURE)
    assert rel == "raw/sources/SFIX0001.pdf"
    assert (synthetic_case_copy / rel).exists()
    source = find_source(synthetic_case_copy, "SFIX0001")
    assert source["raw_path"] == rel


def test_live_service_skips_when_unreachable():
    with pytest.raises(pytest.skip.Exception):
        helpers.live_service("http://127.0.0.1:9", "/readyz")


def test_requires_binary_skips_missing():
    with pytest.raises(pytest.skip.Exception):
        helpers.requires_binary("definitely-not-a-real-binary-xyz")


def test_register_pdf_source_record_matches_schema(synthetic_case_copy):
    import json

    import jsonschema

    from crime_research_kit._runtime.core.casefile import find_source
    from tests.helpers import KIT_ROOT

    helpers.register_pdf_source(synthetic_case_copy, "SFIX0002", helpers.DOCS_FIXTURE)
    schema = json.loads(
        (KIT_ROOT / "docs" / "schemas" / "case" / "source.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(find_source(synthetic_case_copy, "SFIX0002"), schema)
