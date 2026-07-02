"""OCRmyPDF-backed scanned PDF OCR."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

from core.casefile import (
    case_path,
    case_relative,
    file_sha256,
    find_source,
    log_action,
    resolve_case_path,
    update_source,
)


def ocr_source(case_dir: str | Path, source_id: str, *, language: str = "eng", force: bool = False) -> dict[str, Any]:
    """Run OCRmyPDF on a registered PDF source and attach sidecar text."""
    cdir = case_path(case_dir)
    source = find_source(case_dir, source_id)
    raw_path = resolve_case_path(case_dir, source.get("raw_path"))
    if not raw_path or not raw_path.exists():
        raise RuntimeError(f"Source {source_id} has no local raw_path to OCR.")
    sidecar = cdir / "raw" / "sources" / f"{source_id}_ocr.txt"
    output_pdf = cdir / "raw" / "ocr" / f"{source_id}_ocr.pdf"
    if sidecar.exists() and output_pdf.exists() and not force:
        return {"source_id": source_id, "text_path": case_relative(case_dir, sidecar), "skipped": True}
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ocrmypdf",
        "--skip-text",
        "--sidecar",
        str(sidecar),
        "-l",
        language,
        str(raw_path),
        str(output_pdf),
    ]
    completed = subprocess.run(command, cwd=cdir, check=False, capture_output=True, text=True)
    report = _write_report(case_dir, source_id, command, completed, raw_path, sidecar, output_pdf)
    if completed.returncode != 0:
        raise RuntimeError(f"OCR failed for {source_id}. Report: {report}")
    updates = {
        "text_path": case_relative(case_dir, sidecar),
        "text_sha256": file_sha256(sidecar),
        "text_size_bytes": sidecar.stat().st_size,
        "ocr_pdf_path": case_relative(case_dir, output_pdf),
        "ocr_engine": "ocrmypdf",
        "ocr_language": language,
        "ocr_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    update_source(case_dir, source_id, updates)
    log_action(case_dir, "ocr_source", {"source_id": source_id, "language": language, "report": report})
    return {"source_id": source_id, "text_path": updates["text_path"], "ocr_pdf_path": updates["ocr_pdf_path"], "report": report}


def _write_report(
    case_dir: str | Path,
    source_id: str,
    command: list[str],
    completed: subprocess.CompletedProcess[str],
    raw_path: Path,
    sidecar: Path,
    output_pdf: Path,
) -> str:
    report: dict[str, Any] = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_id": source_id,
        "engine": "ocrmypdf",
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "raw_path": case_relative(case_dir, raw_path),
        "sidecar_text_path": case_relative(case_dir, sidecar),
        "ocr_pdf_path": case_relative(case_dir, output_pdf),
    }
    if sidecar.exists():
        report["sidecar_sha256"] = file_sha256(sidecar)
    out = case_path(case_dir) / "staging" / "candidates" / f"ocr_report_{source_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(out)
