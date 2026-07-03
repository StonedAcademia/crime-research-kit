from __future__ import annotations

import csv
import json
from pathlib import Path

from crime_research_kit._runtime.core.casefile import read_jsonl, record_path, resolve_case_path

CURATED_SOURCE_IDS = (
    "S_NSARCHIVE_MKULTRA_CONTEXT_2024",
    "S_CIA_MKULTRA_IG_1963",
    "S_FBI_FINDERS_PART_01",
    "S_FBI_JONESTOWN_HISTORY",
)


def test_cli_capture_preserve_etl_link_score_and_exports(
    populated_mkultra_case: Path,
    ledger_runner,
    ledger_command,
):
    case_dir = populated_mkultra_case

    for source_id in CURATED_SOURCE_IDS:
        ledger_command(ledger_runner, "preserve_source", ["preserve-source", str(case_dir), source_id])

    ledger_command(
        ledger_runner,
        "link_names",
        [
            "link-names",
            str(case_dir),
            "--name",
            "National Security Archive|NSA",
            "--name",
            "MKULTRA|Project MKULTRA|MK-ULTRA",
        ],
    )
    ledger_command(ledger_runner, "validate", ["validate", str(case_dir)])
    ledger_command(ledger_runner, "audit_contradictions", ["audit-contradictions", str(case_dir)])
    ledger_command(ledger_runner, "source_independence", ["audit-source-independence", str(case_dir)])
    ledger_command(ledger_runner, "privacy", ["audit-privacy-redactions", str(case_dir), "--warn-only"])
    ledger_command(ledger_runner, "public_export", ["audit-public-export", str(case_dir), "--warn-only"])
    ledger_command(ledger_runner, "readiness", ["review-narrative-readiness", str(case_dir)])
    ledger_command(ledger_runner, "report", ["report", str(case_dir)])
    ledger_command(ledger_runner, "export_manim", ["export-manim", str(case_dir)])

    timeline_dir = case_dir / "exports" / "timeline"
    ledger_command(
        ledger_runner,
        "export_timeline",
        ["export-timeline", str(case_dir.parent), "--out-dir", str(timeline_dir)],
    )

    sources = read_jsonl(record_path(case_dir, "sources"))
    claims = read_jsonl(record_path(case_dir, "claims"))
    actions = read_jsonl(record_path(case_dir, "research_actions"))
    assert {row["source_id"] for row in sources} >= set(CURATED_SOURCE_IDS)
    assert any(row.get("claim_id") == "C_MKULTRA_E2E_NSARCHIVE_COLLECTION" for row in claims)
    assert any(row.get("action") == "link_names" for row in actions)
    assert (case_dir / "exports" / "evidence_board.md").exists()
    assert (case_dir / "exports" / "manim" / "claims.csv").exists()

    corroborations = list(csv.DictReader((timeline_dir / "corroborations.csv").open(encoding="utf-8")))
    target = next(row for row in corroborations if row["claim_id"] == "C_MKULTRA_E2E_NSARCHIVE_COLLECTION")
    assert target["evidence_level"] == "single_source"
    assert "B:1" in target["source_grades"]


def test_parse_official_pdf_when_documents_extra_is_available(mkultra_live_case: Path, crkit_runner):
    import pytest

    pytest.importorskip("docling")
    output = crkit_runner("parse-source", str(mkultra_live_case), "S_CIA_MKULTRA_IG_1963", "--force")

    text_path = mkultra_live_case / output["text_path"]
    assert text_path.exists()
    assert output["source_id"] == "S_CIA_MKULTRA_IG_1963"
    assert output["skipped"] is False


def test_ocr_boundary_pdf_when_ocr_tooling_is_available(mkultra_live_case: Path, crkit_runner):
    import shutil

    import pytest

    source = next(
        row for row in read_jsonl(record_path(mkultra_live_case, "sources")) if row["source_id"] == "S_FBI_FINDERS_PART_01"
    )
    raw_path = resolve_case_path(mkultra_live_case, source.get("raw_path"))
    if raw_path is None or not raw_path.exists():
        pytest.skip("S_FBI_FINDERS_PART_01 was registered metadata-only in this live run")

    if shutil.which("ocrmypdf") is None or shutil.which("tesseract") is None:
        pytest.skip("ocrmypdf or tesseract is not installed")

    output = crkit_runner("ocr-source", str(mkultra_live_case), "S_FBI_FINDERS_PART_01", "--force")

    assert output["source_id"] == "S_FBI_FINDERS_PART_01"
    assert (mkultra_live_case / output["text_path"]).exists()
    assert (mkultra_live_case / output["ocr_pdf_path"]).exists()


def test_searxng_live_discovery_writes_lead_candidates(mkultra_live_case: Path, crkit_runner):
    import os

    from tests.helpers import live_service

    base = live_service(os.environ.get("CRK_SEARXNG_URL"), "/healthz")
    out = mkultra_live_case / "staging" / "candidates" / "searxng_mkultra.json"

    payload = crkit_runner(
        "discover-sources",
        str(mkultra_live_case),
        "--query",
        "MKULTRA National Security Archive",
        "--searxng-url",
        base,
        "--limit",
        "3",
        "--out",
        str(out),
    )

    assert payload["report"] == str(out)
    assert payload["candidate_count"] >= 0
    assert out.exists()
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["query"] == "MKULTRA National Security Archive"
    assert "candidates" in saved
