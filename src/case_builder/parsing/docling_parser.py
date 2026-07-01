"""Docling-backed source parsing."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from ..casefile import case_path, case_relative, file_sha256, find_source, log_action, resolve_case_path, update_source


def parse_source(case_dir: str | Path, source_id: str, *, force: bool = False) -> dict[str, Any]:
    """Parse a registered local source artifact with Docling."""
    cdir = case_path(case_dir)
    source = find_source(case_dir, source_id)
    existing_text = resolve_case_path(case_dir, source.get("text_path"))
    if existing_text and existing_text.exists() and not force:
        return {"source_id": source_id, "text_path": source.get("text_path"), "skipped": True}
    raw_path = resolve_case_path(case_dir, source.get("raw_path"))
    if not raw_path or not raw_path.exists():
        raise RuntimeError(f"Source {source_id} has no local raw_path to parse.")

    try:
        from docling.document_converter import DocumentConverter  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Docling is not installed. Install the local documents extra.") from exc

    converter = DocumentConverter()
    result = converter.convert(str(raw_path))
    document = result.document
    text = _export_text(document)
    out = cdir / "raw" / "sources" / f"{source_id}_docling.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    report = _write_report(case_dir, source_id, raw_path, out, document)
    updates = {
        "text_path": case_relative(case_dir, out),
        "text_sha256": file_sha256(out),
        "text_size_bytes": out.stat().st_size,
        "parser": "docling",
        "parsed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    update_source(case_dir, source_id, updates)
    log_action(case_dir, "parse_source", {"source_id": source_id, "parser": "docling", "report": report})
    return {"source_id": source_id, "text_path": updates["text_path"], "report": report, "skipped": False}


def _export_text(document: Any) -> str:
    if hasattr(document, "export_to_markdown"):
        return document.export_to_markdown()
    if hasattr(document, "export_to_text"):
        return document.export_to_text()
    return str(document)


def _write_report(case_dir: str | Path, source_id: str, raw_path: Path, text_path: Path, document: Any) -> str:
    report = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_id": source_id,
        "parser": "docling",
        "raw_path": case_relative(case_dir, raw_path),
        "text_path": case_relative(case_dir, text_path),
        "text_sha256": file_sha256(text_path),
        "document_type": type(document).__name__,
    }
    out = case_path(case_dir) / "staging" / "candidates" / f"parse_report_{source_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(out)
