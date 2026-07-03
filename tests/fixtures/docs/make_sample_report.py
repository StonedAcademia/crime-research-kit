"""Regenerate the committed sample_report.pdf fixture.

Run with the documents extra installed:
    uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,documents]' \
        -- python tests/fixtures/docs/make_sample_report.py
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF, provided by the `documents` extra

LINES = [
    "Synthetic evidence fixture for CRK local-stack tests.",
    "The Harbor Study Circle held its first meeting near Riverside Park.",
    "This document is authored test data and is not real evidence.",
]


def build(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in LINES:
        page.insert_text((72, y), line, fontsize=12)
        y += 20
    doc.save(str(path))
    doc.close()


if __name__ == "__main__":
    out = Path(__file__).parent / "sample_report.pdf"
    build(out)
    print(f"wrote {out}")
