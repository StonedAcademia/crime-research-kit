import json

from adapters.ops import query as query_ops
from adapters.ops.safety.policy import record_llm_egress


def register_text_source(case_dir, source_id="STEXT001", public_export=True):
    text_file = case_dir / "raw" / "sources" / f"{source_id}.txt"
    text_file.parent.mkdir(parents=True, exist_ok=True)
    text_file.write_text("Witness statement about the riverside search.", encoding="utf-8")
    row = {
        "source_id": source_id,
        "title": "Test text source",
        "source_type": "news_article",
        "text_path": f"raw/sources/{source_id}.txt",
        "public_export": public_export,
    }
    sources = case_dir / "records" / "sources.jsonl"
    sources.write_text(
        sources.read_text(encoding="utf-8") + json.dumps(row, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_get_source_text_reads_registered_text(synthetic_case_copy):
    register_text_source(synthetic_case_copy)

    result = query_ops.get_source_text(str(synthetic_case_copy), "STEXT001")

    assert result.ok is True
    assert "riverside search" in result.data["text"]
    assert result.data["truncated"] is False


def test_get_source_text_respects_privacy_by_default(synthetic_case_copy):
    register_text_source(synthetic_case_copy, source_id="SPRIV001", public_export=False)

    public = query_ops.get_source_text(str(synthetic_case_copy), "SPRIV001")
    internal = query_ops.get_source_text(str(synthetic_case_copy), "SPRIV001", include_private=True)

    assert public.ok is False
    assert internal.ok is True


def test_get_source_text_truncates_at_max_chars(synthetic_case_copy):
    register_text_source(synthetic_case_copy)

    result = query_ops.get_source_text(str(synthetic_case_copy), "STEXT001", max_chars=10)

    assert len(result.data["text"]) == 10
    assert result.data["truncated"] is True


def test_get_source_text_missing_source_fails(synthetic_case_copy):
    result = query_ops.get_source_text(str(synthetic_case_copy), "SNOPE999")

    assert result.ok is False


def test_record_llm_egress_appends_audit_row(synthetic_case_copy):
    record_llm_egress(synthetic_case_copy, "external-lab-gateway", "fill_packets")

    actions = (synthetic_case_copy / "records" / "research_actions.jsonl").read_text(
        encoding="utf-8"
    )
    last = json.loads(actions.splitlines()[-1])
    assert last["action"] == "llm_egress"
    assert last["details"]["provider"] == "external-lab-gateway"
    assert last["details"]["context"] == "fill_packets"
