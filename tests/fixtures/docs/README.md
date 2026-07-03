# Document test fixtures

`sample_report.pdf` is a tiny, authored single-page PDF with a real text layer
used by the Docling parsing and OCRmyPDF smoke tests. Its extractable text
contains the markers `Harbor Study Circle` and `Riverside Park`.

Regenerate it deterministically with:

    uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,documents]' \
        -- python tests/fixtures/docs/make_sample_report.py

The content is synthetic test data, not real evidence.
