import json

from adapters.interfaces.llm.briefs.audit_brief import write_readiness_brief
from adapters.interfaces.llm.briefs.lane_suggest import suggest_lanes


class FakeModel:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)

        class Reply:
            content = self.response

        return Reply()


def test_suggest_lanes_filters_unknown_and_duplicates():
    response = json.dumps(
        [
            {"lane": "legal-court", "rationale": "Subject mentions charges."},
            {"lane": "missing-persons", "rationale": "Already selected."},
            {"lane": "astral-projection", "rationale": "Not a real lane."},
        ]
    )
    model = FakeModel(response)

    suggestions = suggest_lanes(model, "charges filed after disappearance", ["missing-persons"])

    assert suggestions == [{"lane": "legal-court", "rationale": "Subject mentions charges."}]


def test_suggest_lanes_swallow_malformed_output():
    model = FakeModel("I think you should check the courts!")

    assert suggest_lanes(model, "subject", []) == []


def test_write_readiness_brief_stages_markdown_and_logs(synthetic_case_copy):
    model = FakeModel("- Two claims lack independent sources.\n- One privacy flag is unresolved.")
    audit_results = [
        {"name": "audit_contradictions", "stdout": "0 contradictions"},
        {"name": "audit_privacy_redactions", "stdout": "1 flag"},
    ]

    path = write_readiness_brief(model, str(synthetic_case_copy), audit_results)

    assert "staging/candidates/readiness_brief_" in path.replace("\\", "/")
    content = open(path, encoding="utf-8").read()
    assert "privacy flag" in content
    assert "flags issues for a human reviewer" in content
    actions = (synthetic_case_copy / "records" / "research_actions.jsonl").read_text(
        encoding="utf-8"
    )
    assert "readiness_brief" in actions
    assert "1 flag" in model.prompts[0]
