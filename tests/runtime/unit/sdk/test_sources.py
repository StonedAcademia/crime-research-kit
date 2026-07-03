from __future__ import annotations

import json
from pathlib import Path

from crime_research_kit.sdk import CrkClient, CrkContext
from crime_research_kit.sdk.errors import DEPENDENCY_MISSING, NETWORK_FAILED
from tests.helpers import KIT_ROOT, ledger_command_args


def dry_client_for(case_dir: Path) -> CrkClient:
    return CrkClient(CrkContext(repo_root=KIT_ROOT, cases_root=case_dir.parent, dry_run=True))


def add_raw_source(case_dir: Path, source_id: str) -> None:
    raw = case_dir / "raw" / "sources" / f"{source_id}.pdf"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(b"%PDF-1.4\n% test fixture\n")
    sources = case_dir / "records" / "sources.jsonl"
    row = {
        "public_export": True,
        "raw_path": f"raw/sources/{source_id}.pdf",
        "source_id": source_id,
        "source_type": "document",
        "title": source_id,
    }
    sources.write_text(
        sources.read_text(encoding="utf-8") + json.dumps(row, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_sources_add_plans_manual_registration(synthetic_case_copy: Path):
    result = dry_client_for(synthetic_case_copy).case("synthetic_case").sources.add(
        title="A Story",
        url="https://example.com/story",
        source_type="news_article",
        reliability_grade="B",
        public_export=False,
    )

    args = ledger_command_args(result.diagnostics["command"])
    assert result.ok is True
    assert result.operation == "sources.add"
    assert args[:2] == ["add-source", str(synthetic_case_copy)]
    assert "--no-public-export" in args
    assert result.diagnostics["dry_run"] is True


def test_sources_ingest_url_plans_positionally_with_public_default(synthetic_case_copy: Path):
    public = dry_client_for(synthetic_case_copy).case("synthetic_case").sources.ingest_url(
        "https://example.com/story",
        title="A Story",
        source_type="news_article",
        timeout=15,
    )
    private = dry_client_for(synthetic_case_copy).case("synthetic_case").sources.ingest_url(
        "https://example.com/private-story",
        public_export=False,
    )

    args = ledger_command_args(public.diagnostics["command"])
    private_args = ledger_command_args(private.diagnostics["command"])
    assert public.ok is True
    assert public.operation == "sources.ingest_url"
    assert args[:3] == ["ingest-url", str(synthetic_case_copy), "https://example.com/story"]
    assert args[args.index("--timeout") + 1] == "15"
    assert "--no-public-export" not in args
    assert "--no-public-export" in private_args


def test_sources_preserve_plans_command(synthetic_case_copy: Path):
    result = dry_client_for(synthetic_case_copy).case("synthetic_case").sources.preserve(
        "SDEMO0001",
        archive_url="https://archive.example/story",
    )

    args = ledger_command_args(result.diagnostics["command"])
    assert result.ok is True
    assert result.operation == "sources.preserve"
    assert args[:3] == ["preserve-source", str(synthetic_case_copy), "SDEMO0001"]
    assert "--archive-url" in args


def test_sources_discover_maps_network_errors(synthetic_case_copy: Path, monkeypatch):
    from crime_research_kit._runtime.adapters.ops import sources as source_ops

    def fail_discover(*_args, **_kwargs):
        raise RuntimeError("connection refused by local SearXNG")

    monkeypatch.setattr(source_ops, "discover_sources", fail_discover)

    result = dry_client_for(synthetic_case_copy).case("synthetic_case").sources.discover(query="Jane Doe")

    assert result.ok is False
    assert result.operation == "sources.discover"
    assert result.errors[0].code == NETWORK_FAILED


def test_sources_parse_maps_missing_document_extra(synthetic_case_copy: Path, monkeypatch):
    from crime_research_kit._runtime.adapters.ops import sources as source_ops

    add_raw_source(synthetic_case_copy, "SRAW001")

    def fail_parse(*_args, **_kwargs):
        raise RuntimeError("Docling is not installed. Install the local documents extra.")

    monkeypatch.setattr(source_ops, "parse_source", fail_parse)

    result = dry_client_for(synthetic_case_copy).case("synthetic_case").sources.parse("SRAW001")

    assert result.ok is False
    assert result.operation == "sources.parse"
    assert result.errors[0].code == DEPENDENCY_MISSING


def test_sources_ocr_maps_missing_tooling(synthetic_case_copy: Path, monkeypatch):
    from crime_research_kit._runtime.adapters.ops import sources as source_ops

    add_raw_source(synthetic_case_copy, "SOCR001")

    def fail_ocr(*_args, **_kwargs):
        raise FileNotFoundError("ocrmypdf")

    monkeypatch.setattr(source_ops, "ocr_source", fail_ocr)

    result = dry_client_for(synthetic_case_copy).case("synthetic_case").sources.ocr("SOCR001")

    assert result.ok is False
    assert result.operation == "sources.ocr"
    assert result.errors[0].code == DEPENDENCY_MISSING
