import json
import shutil
from pathlib import Path

from case_builder.cli import build_parser
from case_builder import config
from case_builder.core.memory import remember_research_actions
from case_builder.adapters.io.retrieval import build_evidence_documents
from tests.helpers import KIT_ROOT


def copy_synthetic_case(tmp_path: Path) -> Path:
    case_dir = tmp_path / "synthetic_case"
    shutil.copytree(KIT_ROOT / "data" / "examples" / "synthetic_case", case_dir)
    return case_dir


def test_build_evidence_documents_from_crk_records(tmp_path):
    case_dir = copy_synthetic_case(tmp_path)

    documents = build_evidence_documents(case_dir)
    metadata = [doc.metadata for doc in documents]

    assert any(item["record_type"] == "source" for item in metadata)
    assert any(item["record_type"] == "claims" for item in metadata)
    assert any(item["record_type"] == "events" for item in metadata)
    assert all(item["case_id"] == "synthetic_case" for item in metadata)


def test_build_evidence_documents_respects_public_filter(tmp_path):
    case_dir = copy_synthetic_case(tmp_path)
    claims_path = case_dir / "records" / "claims.jsonl"
    claims_path.write_text(
        claims_path.read_text(encoding="utf-8")
        + json.dumps(
            {
                "claim_id": "CPRIVATE",
                "claim": "Private review-only claim.",
                "status": "unverified",
                "confidence": 0.1,
                "source_ids": ["SDEMO0001"],
                "public_export": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    public_docs = build_evidence_documents(case_dir, include_private=False)
    internal_docs = build_evidence_documents(case_dir, include_private=True)

    assert "Private review-only claim." not in [doc.text for doc in public_docs]
    assert "Private review-only claim." in [doc.text for doc in internal_docs]


def test_remember_research_actions_local_provider(tmp_path):
    case_dir = copy_synthetic_case(tmp_path)
    actions_path = case_dir / "records" / "research_actions.jsonl"
    actions_path.write_text(
        json.dumps(
            {
                "timestamp": "2026-07-01T00:00:00+00:00",
                "action": "test_action",
                "details": {"source_id": "SDEMO0001"},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = remember_research_actions(case_dir, provider="local", limit=5)
    memory_path = case_dir / "staging" / "memory" / "workflow_memory.jsonl"

    assert result["provider"] == "local"
    assert memory_path.exists()
    rows = [json.loads(line) for line in memory_path.read_text(encoding="utf-8").splitlines()]
    assert rows
    assert all(row["evidence"] is False for row in rows)


def test_local_stack_cli_commands_parse():
    parser = build_parser()

    assert parser.parse_args(["discover-sources", "data/cases/x", "--query", "test"]).command == "discover-sources"
    assert parser.parse_args(["parse-source", "data/cases/x", "S1"]).command == "parse-source"
    assert parser.parse_args(["ocr-source", "data/cases/x", "S1"]).command == "ocr-source"
    assert parser.parse_args(["index-case", "data/cases/x"]).command == "index-case"
    assert parser.parse_args(["query-case", "data/cases/x", "question"]).command == "query-case"
    assert parser.parse_args(["remember-research-actions", "data/cases/x"]).command == "remember-research-actions"


def test_self_hosted_service_defaults_read_env(monkeypatch):
    monkeypatch.setenv("CRK_SEARXNG_URL", "http://searxng:8080")
    monkeypatch.setenv("CRK_QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("CRK_QDRANT_HOST", "qdrant")
    monkeypatch.setenv("CRK_QDRANT_PORT", "6333")
    monkeypatch.setenv("CRK_EMBED_MODEL", "local-embed")

    assert config.searxng_url() == "http://searxng:8080"
    assert config.qdrant_url() == "http://qdrant:6333"
    assert config.qdrant_host() == "qdrant"
    assert config.qdrant_port() == 6333
    assert config.embed_model() == "local-embed"


def test_cli_parse_source_reports_clean_error_for_non_case(tmp_path, capsys):
    import pytest

    from case_builder.cli import main

    with pytest.raises(SystemExit) as excinfo:
        main(["parse-source", str(tmp_path / "not_a_case"), "S1"])

    assert excinfo.value.code != 0
