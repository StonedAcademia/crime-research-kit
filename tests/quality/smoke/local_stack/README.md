# Local-stack smoke tests

Fast, hermetic smoke tests for the dependency-heavy local subsystems. Each test
skips cleanly when its optional extra or required binary is absent, so the default
lane stays green.

- `test_parsing.py` — Docling `parse_source` on the committed sample PDF.
- `test_ocr.py`     — OCRmyPDF `ocr_source` (requires `ocrmypdf`/`tesseract`/`gs`).
- `test_discovery.py` — SearXNG `discover_sources` against a mocked httpx transport.

Do **not** create an `__init__.py` here (see Global Constraints).
