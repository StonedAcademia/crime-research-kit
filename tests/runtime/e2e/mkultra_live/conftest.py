from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import httpx
import pytest

from crime_research_kit._runtime.adapters.ops import extraction as extraction_ops
from crime_research_kit._runtime.adapters.ops.runner import CrkRunner
from crime_research_kit._runtime.core.casefile import (
    append_jsonl,
    file_sha256,
    now_utc,
    read_jsonl,
    record_path,
    today,
)
from tests.helpers import KIT_ROOT

MANIFEST_PATH = KIT_ROOT / "docs" / "guides" / "courses" / "samples" / "mkultra" / "sources" / "manifest.json"
REVIEWED_PACKET_PATH = KIT_ROOT / "tests" / "fixtures" / "mkultra_live" / "reviewed_packet.json"
CURATED_SOURCE_IDS = (
    "S_NSARCHIVE_MKULTRA_CONTEXT_2024",
    "S_CIA_MKULTRA_IG_1963",
    "S_FBI_FINDERS_PART_01",
    "S_FBI_JONESTOWN_HISTORY",
)
PRIMARY_SOURCE_ID = "S_NSARCHIVE_MKULTRA_CONTEXT_2024"
OFFICIAL_PDF_SOURCE_ID = "S_CIA_MKULTRA_IG_1963"
OCR_SOURCE_ID = "S_FBI_FINDERS_PART_01"


def pytest_collection_modifyitems(config, items):
    for item in items:
        try:
            parts = Path(str(item.fspath)).resolve().relative_to(KIT_ROOT / "tests").parts
        except ValueError:
            continue
        if "mkultra_live" in parts:
            item.add_marker("live")
            if os.environ.get("CRK_LIVE_MKULTRA") != "1":
                item.add_marker(pytest.mark.skip(reason="set CRK_LIVE_MKULTRA=1 to run live MKULTRA workflow tests"))


@pytest.fixture(scope="session")
def mkultra_live_case(tmp_path_factory: pytest.TempPathFactory) -> Path:
    case_dir = tmp_path_factory.mktemp("mkultra_live") / "mkultra_course_live"
    _init_case(case_dir)
    _register_curated_sources(case_dir)
    return case_dir


@pytest.fixture(scope="session")
def populated_mkultra_case(mkultra_live_case: Path) -> Path:
    _draft_and_import_reviewed_packet(mkultra_live_case)
    return mkultra_live_case


@pytest.fixture
def ledger_runner() -> CrkRunner:
    return CrkRunner(repo_root=KIT_ROOT, dry_run=False)


@pytest.fixture
def ledger_command():
    return run_ledger


@pytest.fixture
def crkit_runner():
    return run_crkit


def manifest_sources() -> dict[str, dict[str, Any]]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {str(row["source_id"]): row for row in data["sources"]}


def run_ledger(runner: CrkRunner, name: str, args: Iterable[str]):
    result = runner.run(name, list(args))
    assert result.ok, "\n".join(result.errors) or result.stderr
    return result


def run_crkit(*args: str, env: dict[str, str] | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-m", "crime_research_kit._runtime.cli", *args],
        cwd=KIT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    stdout = completed.stdout.strip()
    return json.loads(stdout) if stdout.startswith("{") else {"stdout": stdout}


def _init_case(case_dir: Path) -> None:
    if (case_dir / "case.json").exists():
        return
    runner = CrkRunner(repo_root=KIT_ROOT, dry_run=False)
    run_ledger(
        runner,
        "init_case",
        [
            "init-case",
            str(case_dir),
            "--title",
            "MKULTRA Live E2E Case",
            "--scope",
            "Temporary live workflow case for the MKULTRA course guide.",
            "--public-interest",
            "Testing source-traceable documentary research workflows.",
        ],
    )


def _register_curated_sources(case_dir: Path) -> None:
    sources_by_id = manifest_sources()
    existing = {row.get("source_id") for row in read_jsonl(record_path(case_dir, "sources"))}
    for source_id in CURATED_SOURCE_IDS:
        if source_id in existing:
            continue
        row = sources_by_id[source_id]
        raw_rel = str(row["raw_path"] or f"raw/downloads/{source_id}")
        raw_path = case_dir / raw_rel
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        response = httpx.get(str(row["url"]), follow_redirects=True, timeout=60)
        if not response.is_success:
            _append_metadata_only_source(case_dir, row, response.status_code)
            continue
        raw_path.write_bytes(response.content)

        content_type = response.headers.get("content-type", "")
        text_rel = row.get("text_path") if _is_textual(raw_rel, content_type) else None
        text_sha = None
        if text_rel:
            text_path = case_dir / str(text_rel)
            text_path.parent.mkdir(parents=True, exist_ok=True)
            text = _extract_text(response.content, content_type)
            text_path.write_text(text, encoding="utf-8")
            text_sha = file_sha256(text_path)

        append_jsonl(
            record_path(case_dir, "sources"),
            {
                "source_id": source_id,
                "title": row["title"],
                "source_type": row["source_type"],
                "author": None,
                "publisher": row.get("publisher"),
                "date_published": row.get("date_published"),
                "date_accessed": today(),
                "url": row.get("url"),
                "archive_url": None,
                "raw_path": raw_rel,
                "text_path": text_rel,
                "content_type": content_type or None,
                "capture_method": "ingest_url",
                "capture_timestamp": now_utc(),
                "raw_sha256": file_sha256(raw_path),
                "text_sha256": text_sha,
                "preservation_status": "captured",
                "preservation_warnings": [],
                "reliability_grade": row["reliability_grade"],
                "independence_group": row.get("publisher"),
                "notes": "Live MKULTRA E2E capture from tracked course manifest.",
                "public_export": True,
            },
        )


def _append_metadata_only_source(case_dir: Path, row: dict[str, Any], status_code: int) -> None:
    append_jsonl(
        record_path(case_dir, "sources"),
        {
            "source_id": row["source_id"],
            "title": row["title"],
            "source_type": row["source_type"],
            "author": None,
            "publisher": row.get("publisher"),
            "date_published": row.get("date_published"),
            "date_accessed": today(),
            "url": row.get("url"),
            "archive_url": None,
            "raw_path": None,
            "text_path": None,
            "content_type": None,
            "capture_method": "manual_registration",
            "capture_timestamp": now_utc(),
            "raw_sha256": None,
            "text_sha256": None,
            "preservation_status": "metadata_only",
            "preservation_warnings": [f"live capture returned HTTP {status_code}"],
            "reliability_grade": row["reliability_grade"],
            "independence_group": row.get("publisher"),
            "notes": f"Live MKULTRA E2E registered metadata only; source returned HTTP {status_code}.",
            "public_export": True,
        },
    )


def _is_textual(raw_rel: str, content_type: str) -> bool:
    lowered = raw_rel.lower()
    return lowered.endswith((".html", ".htm", ".txt")) or "html" in content_type or content_type.startswith("text/")


def _extract_text(raw: bytes, content_type: str) -> str:
    from crime_research_kit._runtime.adapters.ops.casework.records.intake.web import extract_html_text

    if "html" in content_type:
        text, _meta = extract_html_text(raw, content_type)
        return text
    return raw.decode("utf-8", errors="replace")


def _draft_and_import_reviewed_packet(case_dir: Path) -> None:
    claims_path = record_path(case_dir, "claims")
    if any(row.get("claim_id") == "C_MKULTRA_E2E_NSARCHIVE_COLLECTION" for row in read_jsonl(claims_path)):
        return
    runner = CrkRunner(repo_root=KIT_ROOT, dry_run=False)
    run_ledger(
        runner,
        "draft_extraction",
        [
            "draft-extraction",
            str(case_dir),
            PRIMARY_SOURCE_ID,
            "--template",
            "generic",
            "--excerpt-chars",
            "4000",
        ],
    )
    packet_name = f"{PRIMARY_SOURCE_ID}_extraction.json"
    packet = json.loads(REVIEWED_PACKET_PATH.read_text(encoding="utf-8"))
    saved = extraction_ops.save_packet(str(case_dir), packet_name, packet)
    assert saved.ok, "\n".join(saved.errors)
    imported = extraction_ops.import_extraction(
        runner,
        str(case_dir),
        str(case_dir / "staging" / "extractions" / packet_name),
        confirm=True,
    )
    assert imported.ok, "\n".join(imported.errors) or imported.stderr
