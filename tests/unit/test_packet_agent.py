import json

import pytest

from case_builder.llm.packet_agent import PacketAgentError, bounded_context, fill_packet


class FakeModel:
    """Returns queued responses; records prompts for assertions."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)

        class Reply:
            content = self.responses.pop(0)

        return Reply()


TEMPLATE = {
    "source_id": "S0001",
    "entities": [],
    "claims": [],
    "events": [],
}


def filled_payload(**overrides):
    payload = {
        "source_id": "S0001",
        "entities": [{"name": "A Witness", "role": "witness", "source_ids": ["S0001"]}],
        "claims": [
            {
                "claim": "A search occurred near the river.",
                "source_ids": ["S0001"],
                "confidence": 0.9,
                "status": "corroborated",
                "public_export": True,
            }
        ],
        "events": [],
    }
    payload.update(overrides)
    return payload


def test_fill_packet_hardens_assertion_records():
    model = FakeModel([json.dumps(filled_payload())])

    result = fill_packet(model, TEMPLATE, "Search near the river.", source_id="S0001")

    claim = result["claims"][0]
    assert claim["status"] == "unverified"
    assert claim["confidence"] <= 0.3
    assert claim["public_export"] is False
    assert result["entities"][0]["public_export"] is False


def test_fill_packet_strips_code_fences():
    fenced = "```json\n" + json.dumps(filled_payload()) + "\n```"
    model = FakeModel([fenced])

    result = fill_packet(model, TEMPLATE, "text", source_id="S0001")

    assert result["claims"][0]["source_ids"] == ["S0001"]


def test_fill_packet_retries_once_with_error_feedback():
    model = FakeModel(["not json at all", json.dumps(filled_payload())])

    result = fill_packet(model, TEMPLATE, "text", source_id="S0001")

    assert len(model.prompts) == 2
    assert "not valid JSON" in model.prompts[1]
    assert result["claims"]


def test_fill_packet_fails_after_two_bad_responses():
    model = FakeModel(["nope", "still nope"])

    with pytest.raises(PacketAgentError):
        fill_packet(model, TEMPLATE, "text", source_id="S0001")


def test_fill_packet_rejects_invented_source_ids():
    bad = filled_payload()
    bad["claims"][0]["source_ids"] = ["SFAKE999"]
    model = FakeModel([json.dumps(bad), json.dumps(bad)])

    with pytest.raises(PacketAgentError, match="S0001"):
        fill_packet(model, TEMPLATE, "text", source_id="S0001")


def test_fill_packet_rejects_new_top_level_keys():
    bad = filled_payload(surprise_key=[{"x": 1}])
    model = FakeModel([json.dumps(bad), json.dumps(bad)])

    with pytest.raises(PacketAgentError, match="surprise_key"):
        fill_packet(model, TEMPLATE, "text", source_id="S0001")


def test_fill_packet_rejects_uncited_guilt_labels():
    bad = filled_payload()
    bad["entities"][0]["role"] = "suspect"
    model = FakeModel([json.dumps(bad), json.dumps(bad)])

    with pytest.raises(PacketAgentError, match="guilt"):
        fill_packet(model, TEMPLATE, "text", source_id="S0001")


def test_bounded_context_keeps_head_and_tail():
    text = "HEAD " + ("x" * 50000) + " TAIL"

    bounded = bounded_context(text, 1000)

    assert len(bounded) <= 1000 + len("\n...[truncated]...\n")
    assert bounded.startswith("HEAD")
    assert bounded.endswith("TAIL")
