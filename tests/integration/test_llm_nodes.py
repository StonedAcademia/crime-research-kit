import json
from pathlib import Path

from case_builder.graph.llm_nodes import (
    fill_packets_node,
    readiness_brief_node,
    suggest_lanes_node,
)
from case_builder.ops.runner import CrkRunner
from tests.helpers import KIT_ROOT


class FakeModel:
    def __init__(self, response):
        self.response = response

    def invoke(self, prompt):
        class Reply:
            content = self.response

        return Reply()


def execute_runner() -> CrkRunner:
    return CrkRunner(repo_root=KIT_ROOT, dry_run=False)


def test_llm_nodes_skip_without_flag_factory_or_execute():
    dry = CrkRunner(repo_root=KIT_ROOT, dry_run=True)
    factory = lambda: FakeModel("[]")

    assert suggest_lanes_node(execute_runner(), None)({"llm_enabled": True})["status"] == "lane_suggestions_skipped"
    assert suggest_lanes_node(execute_runner(), factory)({})["status"] == "lane_suggestions_skipped"
    assert suggest_lanes_node(dry, factory)({"llm_enabled": True})["status"] == "lane_suggestions_skipped"
    assert fill_packets_node(dry, factory)({"llm_enabled": True})["status"] == "fill_skipped"
    assert readiness_brief_node(dry, factory)({"llm_enabled": True})["status"] == "brief_skipped"


def test_suggest_lanes_node_records_suggestions():
    response = json.dumps([{"lane": "legal-court", "rationale": "Charges are mentioned."}])
    node = suggest_lanes_node(execute_runner(), lambda: FakeModel(response))

    update = node({"llm_enabled": True, "subject": "charges filed", "lanes": ["missing-persons"]})

    assert update["status"] == "lanes_suggested"
    assert update["lane_suggestions"] == [{"lane": "legal-court", "rationale": "Charges are mentioned."}]


def test_fill_packets_node_fills_and_saves_staged_packet(synthetic_case_copy, monkeypatch):
    monkeypatch.delenv("CRK_MODEL", raising=False)
    source_id = "SDEMO0001"
    text_file = synthetic_case_copy / "raw" / "sources" / f"{source_id}.txt"
    text_file.parent.mkdir(parents=True, exist_ok=True)
    text_file.write_text("A search occurred near the river.", encoding="utf-8")
    sources_path = synthetic_case_copy / "records" / "sources.jsonl"
    rows = [json.loads(line) for line in sources_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["source_id"] = source_id
    rows[0]["text_path"] = f"raw/sources/{source_id}.txt"
    sources_path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")

    template = {"source_id": source_id, "claims": []}
    packet_dir = synthetic_case_copy / "staging" / "extractions"
    packet_dir.mkdir(parents=True, exist_ok=True)
    (packet_dir / f"{source_id}_extraction.json").write_text(json.dumps(template), encoding="utf-8")

    filled = {
        "source_id": source_id,
        "claims": [{"claim": "Search near river.", "source_ids": [source_id]}],
    }
    node = fill_packets_node(execute_runner(), lambda: FakeModel(json.dumps(filled)))

    update = node(
        {
            "llm_enabled": True,
            "case_dir": str(synthetic_case_copy),
            "packets": [f"{source_id}_extraction.json"],
        }
    )

    assert update["status"] == "packets_filled"
    saved = json.loads((packet_dir / f"{source_id}_extraction.json").read_text(encoding="utf-8"))
    assert saved["claims"][0]["status"] == "unverified"
    assert saved["claims"][0]["public_export"] is False


def test_fill_packets_node_records_agent_failures_without_raising(synthetic_case_copy):
    packet_dir = synthetic_case_copy / "staging" / "extractions"
    packet_dir.mkdir(parents=True, exist_ok=True)
    (packet_dir / "SDEMO0001_extraction.json").write_text(
        json.dumps({"source_id": "SDEMO0001", "claims": []}),
        encoding="utf-8",
    )

    node = fill_packets_node(execute_runner(), lambda: FakeModel("never json"))

    update = node(
        {
            "llm_enabled": True,
            "case_dir": str(synthetic_case_copy),
            "packets": ["SDEMO0001_extraction.json"],
        }
    )

    assert update["status"] in {"packets_filled", "error"}
    assert update["errors"]


def test_readiness_brief_node_writes_brief_from_audit_results(synthetic_case_copy):
    node = readiness_brief_node(execute_runner(), lambda: FakeModel("- One flag."))
    state = {
        "llm_enabled": True,
        "case_dir": str(synthetic_case_copy),
        "tool_results": [
            {"name": "audit_contradictions", "stdout": "0 contradictions"},
            {"name": "audit_privacy_redactions", "stdout": "1 flag"},
            {"name": "export_manim", "stdout": "not an audit"},
        ],
    }

    update = node(state)

    assert update["status"] == "readiness_brief_written"
    briefs = list((synthetic_case_copy / "staging" / "candidates").glob("readiness_brief_*.md"))
    assert briefs


def test_pipeline_list_includes_llm_nodes_in_order():
    from case_builder.graph.runner import pipeline_nodes_list

    names = [name for name, _ in pipeline_nodes_list(execute_runner(), use_interrupt=False, model_factory=None)]

    assert names.index("suggest_lanes") == names.index("infer_lanes") + 1
    assert names.index("fill_packets") == names.index("draft_packets") + 1
    assert names.index("readiness_brief") == names.index("readiness_audit") + 1
    assert names.index("packet_review_gate") == names.index("fill_packets") + 1
