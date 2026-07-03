from __future__ import annotations

import json
from pathlib import Path

from crime_research_kit.sdk import CrkClient, CrkContext
from crime_research_kit.sdk.errors import INVALID_INPUT, PRIVACY_BLOCKED


def add_private_claim(case_dir: Path) -> None:
    claims = case_dir / "records" / "claims.jsonl"
    row = {
        "claim_id": "CPRIVATE",
        "claim": "Private claim.",
        "status": "unverified",
        "confidence": 0.1,
        "source_ids": ["SDEMO0001"],
        "public_export": False,
    }
    claims.write_text(
        claims.read_text(encoding="utf-8") + json.dumps(row, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def add_public_claim(case_dir: Path, claim_id: str) -> None:
    claims = case_dir / "records" / "claims.jsonl"
    row = {
        "claim_id": claim_id,
        "claim": "Additional public claim.",
        "status": "unverified",
        "confidence": 0.1,
        "source_ids": ["SDEMO0001"],
        "public_export": True,
    }
    claims.write_text(
        claims.read_text(encoding="utf-8") + json.dumps(row, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def register_text_source(case_dir: Path, source_id: str, *, public_export: bool = True) -> None:
    text_file = case_dir / "raw" / "sources" / f"{source_id}.txt"
    text_file.parent.mkdir(parents=True, exist_ok=True)
    text_file.write_text("Registered source text for SDK tests.", encoding="utf-8")
    row = {
        "source_id": source_id,
        "title": source_id,
        "source_type": "document",
        "reliability_grade": "B",
        "text_path": text_file.relative_to(case_dir).as_posix(),
        "public_export": public_export,
    }
    sources = case_dir / "records" / "sources.jsonl"
    sources.write_text(
        sources.read_text(encoding="utf-8") + json.dumps(row, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sdk_client_for(case_dir: Path) -> CrkClient:
    return CrkClient(CrkContext(cases_root=case_dir.parent))


def test_client_lists_case_slugs(synthetic_case_copy: Path):
    result = sdk_client_for(synthetic_case_copy).cases.list()

    assert result.ok is True
    assert result.operation == "cases.list"
    assert result.data["cases"] == ["synthetic_case"]
    assert result.counts == {"cases": 1}


def test_case_info_counts_public_records_by_default(synthetic_case_copy: Path):
    add_private_claim(synthetic_case_copy)
    case = sdk_client_for(synthetic_case_copy).case("synthetic_case")

    public = case.info()
    internal = case.info(include_private=True)

    assert public.ok is True
    assert public.operation == "case.info"
    assert public.data["include_private"] is False
    assert internal.data["include_private"] is True
    assert internal.counts["claims"] == public.counts["claims"] + 1
    assert public.data["record_counts"] == public.counts


def test_records_list_filters_private_rows_by_default(synthetic_case_copy: Path):
    add_private_claim(synthetic_case_copy)
    case = sdk_client_for(synthetic_case_copy).case("synthetic_case")

    public = case.records.list("claims")
    internal = case.with_privacy(include_private=True).records.list("claims")

    assert public.ok is True
    assert all(row.get("claim_id") != "CPRIVATE" for row in public.data["records"])
    assert public.counts["filtered"] == 1
    assert any(row.get("claim_id") == "CPRIVATE" for row in internal.data["records"])


def test_records_list_limit_marks_truncated(synthetic_case_copy: Path):
    add_public_claim(synthetic_case_copy, "CPUBLIC2")

    result = sdk_client_for(synthetic_case_copy).case("synthetic_case").records.list("claims", limit=1)

    assert result.ok is True
    assert len(result.data["records"]) == 1
    assert result.data["truncated"] is True


def test_records_list_unknown_type_returns_sdk_error(synthetic_case_copy: Path):
    result = sdk_client_for(synthetic_case_copy).case("synthetic_case").records.list("nonsense")

    assert result.ok is False
    assert result.operation == "records.list"
    assert result.errors[0].code == INVALID_INPUT


def test_source_text_respects_privacy_default(synthetic_case_copy: Path):
    register_text_source(synthetic_case_copy, "STEXT001")
    register_text_source(synthetic_case_copy, "SPRIV001", public_export=False)
    case = sdk_client_for(synthetic_case_copy).case("synthetic_case")

    public = case.records.source_text("STEXT001", max_chars=10)
    private = case.records.source_text("SPRIV001")
    internal = case.records.source_text("SPRIV001", include_private=True)

    assert public.ok is True
    assert public.data["text"] == "Registered"
    assert public.data["truncated"] is True
    assert private.ok is False
    assert private.errors[0].code == PRIVACY_BLOCKED
    assert internal.ok is True
