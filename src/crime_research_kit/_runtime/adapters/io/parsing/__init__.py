"""Local document parsing and OCR helpers."""

from __future__ import annotations

from .docling_parser import parse_source
from .ocr import ocr_source

__all__ = ["ocr_source", "parse_source"]
