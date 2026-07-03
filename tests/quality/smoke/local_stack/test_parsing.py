import sys
from pathlib import Path

import pytest

from tests import helpers
from crime_research_kit._runtime.adapters.io.parsing.docling_parser import parse_source


def test_parse_source_extracts_text(synthetic_case_copy: Path):
    helpers.requires_extra("docling")
    helpers.register_pdf_source(synthetic_case_copy, "SPARSE1", helpers.DOCS_FIXTURE)

    result = parse_source(synthetic_case_copy, "SPARSE1")

    text_path = synthetic_case_copy / result["text_path"]
    assert text_path.exists()
    assert "Harbor Study Circle" in text_path.read_text(encoding="utf-8")
    assert result["skipped"] is False


def test_parse_source_is_idempotent(synthetic_case_copy: Path):
    helpers.requires_extra("docling")
    helpers.register_pdf_source(synthetic_case_copy, "SPARSE2", helpers.DOCS_FIXTURE)

    parse_source(synthetic_case_copy, "SPARSE2")
    again = parse_source(synthetic_case_copy, "SPARSE2")

    assert again["skipped"] is True


def test_parse_source_without_docling_raises(monkeypatch, synthetic_case_copy: Path):
    helpers.register_pdf_source(synthetic_case_copy, "SPARSE3", helpers.DOCS_FIXTURE)
    monkeypatch.setitem(sys.modules, "docling.document_converter", None)

    with pytest.raises(RuntimeError, match="[Dd]ocling"):
        parse_source(synthetic_case_copy, "SPARSE3")
