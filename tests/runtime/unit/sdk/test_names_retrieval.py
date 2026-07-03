from pathlib import Path

from adapters.ops import query as query_ops
from adapters.ops.result import OpResult
from crime_research_kit.sdk import CrkClient, CrkContext
from tests.helpers import KIT_ROOT, ledger_subcommand


def test_names_link_uses_runner(synthetic_case_copy: Path):
    client = CrkClient(CrkContext(cases_root=synthetic_case_copy.parent, repo_root=KIT_ROOT, dry_run=True))

    result = client.case("synthetic_case").names.link(names=["Jane Doe"])

    assert result.ok is True
    assert result.operation == "names.link"
    assert ledger_subcommand(result.diagnostics["command"]) == "link-names"
    assert "Jane Doe" in result.diagnostics["command"]


def test_retrieval_query_uses_settings_and_sdk_result(monkeypatch, synthetic_case_copy: Path):
    calls = {}

    def fake_query_case(
        case_dir: str,
        query_text: str,
        *,
        include_private: bool,
        qdrant_url: str | None,
        collection: str | None,
        embed_model: str | None,
        top_k: int,
    ) -> OpResult:
        calls.update(
            {
                "case_dir": case_dir,
                "query_text": query_text,
                "include_private": include_private,
                "qdrant_url": qdrant_url,
                "collection": collection,
                "embed_model": embed_model,
                "top_k": top_k,
            }
        )
        return OpResult(name="query_case", data={"matches": [{"source_id": "SDEMO0001"}]})

    monkeypatch.setattr(query_ops, "query_case", fake_query_case)
    client = CrkClient(
        CrkContext(
            cases_root=synthetic_case_copy.parent,
            include_private=True,
            settings={"qdrant_url": "http://qdrant.local", "embed_model": "embedder"},
        )
    )

    result = client.case("synthetic_case").retrieval.query("who is cited?", top_k=3)

    assert result.ok is True
    assert result.operation == "retrieval.query"
    assert result.data["matches"] == [{"source_id": "SDEMO0001"}]
    assert calls == {
        "case_dir": str(synthetic_case_copy),
        "query_text": "who is cited?",
        "include_private": True,
        "qdrant_url": "http://qdrant.local",
        "collection": None,
        "embed_model": "embedder",
        "top_k": 3,
    }
