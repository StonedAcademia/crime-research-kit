from pathlib import Path

from tests import helpers
from crime_research_kit._runtime.adapters.io.parsing.ocr import ocr_source


def _require_ocr_binaries():
    for binary in ("ocrmypdf", "tesseract", "gs"):
        helpers.requires_binary(binary)


def test_ocr_source_writes_sidecar_and_pdf(synthetic_case_copy: Path):
    _require_ocr_binaries()
    helpers.register_pdf_source(synthetic_case_copy, "SOCR1", helpers.DOCS_FIXTURE)

    result = ocr_source(synthetic_case_copy, "SOCR1")

    sidecar = synthetic_case_copy / result["text_path"]
    output_pdf = synthetic_case_copy / result["ocr_pdf_path"]
    assert sidecar.exists()
    assert output_pdf.exists()


def test_ocr_source_is_idempotent(synthetic_case_copy: Path):
    _require_ocr_binaries()
    helpers.register_pdf_source(synthetic_case_copy, "SOCR2", helpers.DOCS_FIXTURE)

    ocr_source(synthetic_case_copy, "SOCR2")
    again = ocr_source(synthetic_case_copy, "SOCR2")

    assert again["skipped"] is True
