from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from crime_research_kit._runtime.adapters.ops import extraction as extraction_ops
from crime_research_kit._runtime.adapters.ops.runner import CrkRunner
from crime_research_kit._runtime.core.casefile import read_jsonl, record_path
from tests.helpers import KIT_ROOT
from tests.runtime.e2e.mkultra_live.source_seed import PRIMARY_SOURCE_ID, register_curated_sources

REVIEWED_PACKET_PATH = KIT_ROOT / "tests" / "fixtures" / "mkultra_live" / "reviewed_packet.json"


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
    items.sort(key=_live_item_priority)


def _live_item_priority(item) -> tuple[int, str]:
    if "mkultra_live" not in str(item.fspath):
        return (100, item.nodeid)
    if "test_parse_official_pdf" in item.nodeid:
        return (0, item.nodeid)
    if "test_ocr_heavy_official_pdf" in item.nodeid:
        return (1, item.nodeid)
    return (10, item.nodeid)


@pytest.fixture(scope="session")
def mkultra_live_case(tmp_path_factory: pytest.TempPathFactory) -> Path:
    case_dir = tmp_path_factory.mktemp("mkultra_live") / "mkultra_course_live"
    _init_case(case_dir)
    register_curated_sources(case_dir)
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
