# tc-c-kit LLM Layer + Agent Nodes (Phase 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a provider-pluggable LLM layer (local Ollama default) and three bounded agent capabilities — extraction-packet filling, readiness-audit reviewer briefs, and lane suggestions — wired into the Phase 2 pipeline as skippable nodes.

**Architecture:** A `case_builder/llm/` package holds provider resolution (`CRK_MODEL` env, `provider:model` spec) and three pure agent functions that accept any object with `.invoke(prompt) -> obj-with-.content` — so tests inject fakes and never import langchain. Three new graph nodes (`suggest_lanes`, `fill_packets`, `readiness_brief`) run only when `llm_enabled` is set, a model factory is provided, and the runner is not in dry-run; otherwise they skip, preserving all Phase 2 behavior. Safety: filled packets pass the guilt-label lint and automation defaults before staged save; non-local providers are recorded in the audit log via a new `ops.policy.record_llm_egress`.

**Tech Stack:** Python ≥3.10; `langchain` + `langchain-ollama` behind a new `[llm]` extra (only imported inside `get_chat_model`); pytest with fake models (no network, no LLM in CI).

## Global Constraints

- Repo root: `<project_root>/`. All paths relative to it. Run tests with `cd <repo root> && .venv/bin/python -m pytest <path> -v` (baseline after Phase 2: 110 passed).
- Modules stay under **200 non-comment LOC**; every package dir under `src/case_builder/` has a `README.md` (enforced by `tests/test_case_builder_structure.py`).
- `[project] dependencies = []` stays empty — langchain goes in the new `llm` optional extra. Install into the venv with `uv pip install -p .venv/bin/python -e '.[llm]' -q` (the venv has no pip).
- Agent functions are **bounded, single-purpose calls with structured output** — no tool use, no loops beyond one retry-with-feedback (spec: "not free-roaming agents").
- Agent output invariants (spec): schema-conform structure, `status: unverified` + capped confidence + `public_export: false` on assertion records, never invent source IDs, guilt-label lint must pass, LLM readiness output *flags, never decides*.
- Behavior preservation: `tests/test_case_builder.py` and `tests/test_pipeline_runner.py` pass unmodified — LLM nodes skip by default.
- Existing interfaces consumed (Phase 1–2, already landed): `OpResult`, `CrkRunner`, `ops.policy.apply_automation_defaults / lint_guilt_labels / ensure_staged_write / PolicyError`, `ops.extraction.read_packet / save_packet / list_packets`, `ops.query.get_records`, `casefile.find_source / resolve_case_path / log_action / ensure_case / CasefileError`, `graph.runner.pipeline_nodes_list / run_sequential / build_case_builder_graph`, `models.state.CaseBuilderState`, `agents.source_lanes.LANE_TRIGGERS`.
- Commit per task, conventional-commit style, ending with:

  ```
  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```

## File Structure (end state)

```
src/case_builder/llm/
  __init__.py       # re-exports get_chat_model, active_model_spec, is_local_provider
  README.md
  provider.py       # CRK_MODEL parsing, get_chat_model(), locality check
  packet_agent.py   # fill_packet() with parse/validate/retry, bounded context
  audit_brief.py    # write_readiness_brief()
  lane_suggest.py   # suggest_lanes()
src/case_builder/graph/llm_nodes.py   # suggest_lanes_node, fill_packets_node, readiness_brief_node
src/case_builder/ops/query.py         # MODIFIED: + get_source_text()
src/case_builder/ops/policy.py        # MODIFIED: + record_llm_egress()
src/case_builder/graph/runner.py      # MODIFIED: model_factory threading
src/case_builder/graph/state.py       # MODIFIED: + llm_enabled, lane_suggestions
src/case_builder/models/state.py      # MODIFIED: same fields
src/case_builder/app/service.py       # MODIFIED: model factory selection
src/case_builder/cli.py               # MODIFIED: plan --llm flag
pyproject.toml                        # MODIFIED: [llm] extra
docs/case-builder-langgraph.md        # MODIFIED: LLM nodes + CRK_MODEL docs

New tests:
tests/test_ops_source_text.py
tests/test_llm_provider.py
tests/test_packet_agent.py
tests/test_llm_helpers.py
tests/test_llm_nodes.py
```

Out of scope (later phases): MCP server (Phase 4), `docs/lanes.json` consolidation (Phase 5), retrieval-index chunk *selection* (the packet agent bounds context by head+tail truncation with the retrieval upgrade left to a follow-up — recorded in Task 3's module docstring).

---

### Task 1: `ops.query.get_source_text` + `ops.policy.record_llm_egress`

**Files:**
- Modify: `src/case_builder/ops/query.py` (append one function)
- Modify: `src/case_builder/ops/policy.py` (append one function)
- Test: `tests/test_ops_source_text.py`

**Interfaces:**
- Consumes: `casefile.find_source(case_dir, source_id)` (raises `CasefileError` when missing), `casefile.resolve_case_path(case_dir, value)`, `casefile.log_action(case_dir, action, details)`, `ops.policy.filter_public`, `OpResult`.
- Produces:
  - `ops.query.get_source_text(case_dir: str, source_id: str, *, include_private: bool = False, max_chars: int | None = None) -> OpResult` — `data={"source_id", "text", "text_path", "truncated": bool}`; `ok=False` when the source is missing, is `public_export: false` without `include_private`, or has no readable `text_path`.
  - `ops.policy.record_llm_egress(case_dir: str | Path, provider: str, context: str) -> None` — appends an `llm_egress` row to `research_actions.jsonl`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_ops_source_text.py`:

```python
import json

from case_builder.ops import query as query_ops
from case_builder.ops.policy import record_llm_egress


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
        sources.read_text(encoding="utf-8") + json.dumps(row, sort_keys=True) + "\n", encoding="utf-8"
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
    record_llm_egress(synthetic_case_copy, "anthropic", "fill_packets")

    actions = (synthetic_case_copy / "records" / "research_actions.jsonl").read_text(encoding="utf-8")
    last = json.loads(actions.splitlines()[-1])
    assert last["action"] == "llm_egress"
    assert last["details"]["provider"] == "anthropic"
    assert last["details"]["context"] == "fill_packets"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <project_root>/ && .venv/bin/python -m pytest tests/test_ops_source_text.py -v`
Expected: FAIL with `AttributeError` (`get_source_text` / `record_llm_egress` not defined)

- [ ] **Step 3: Write minimal implementation**

Append to `src/case_builder/ops/query.py` (extend the existing `from ..casefile import ...` line to also import `CasefileError`, `find_source`, `resolve_case_path`):

```python
def get_source_text(
    case_dir: str,
    source_id: str,
    *,
    include_private: bool = False,
    max_chars: int | None = None,
) -> OpResult:
    try:
        source = find_source(case_dir, source_id)
    except CasefileError as exc:
        return OpResult(name="get_source_text", ok=False, errors=[str(exc)])
    if source.get("public_export") is False and not include_private:
        return OpResult(
            name="get_source_text",
            ok=False,
            errors=[f"Source {source_id} is public_export=false; pass include_private=True for internal review."],
        )
    text_path = resolve_case_path(case_dir, source.get("text_path"))
    if not text_path or not text_path.exists():
        return OpResult(name="get_source_text", ok=False, errors=[f"Source {source_id} has no readable text_path."])
    text = text_path.read_text(encoding="utf-8")
    truncated = max_chars is not None and len(text) > max_chars
    return OpResult(
        name="get_source_text",
        data={
            "source_id": source_id,
            "text": text[:max_chars] if truncated else text,
            "text_path": str(source.get("text_path")),
            "truncated": truncated,
        },
    )
```

Append to `src/case_builder/ops/policy.py` (add `from ..casefile import log_action` to its imports; `ensure_case` is already imported):

```python
def record_llm_egress(case_dir: str | Path, provider: str, context: str) -> None:
    """Audit-log that source text was sent to a non-local LLM provider."""
    log_action(
        ensure_case(case_dir),
        "llm_egress",
        {"provider": provider, "context": context, "note": "source text left the machine"},
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd <project_root>/ && .venv/bin/python -m pytest tests/test_ops_source_text.py tests/test_case_builder_structure.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/case_builder/ops/query.py src/case_builder/ops/policy.py tests/test_ops_source_text.py
git commit -m "feat(ops): add source text reads and llm egress audit logging

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: LLM provider layer

**Files:**
- Create: `src/case_builder/llm/__init__.py`, `src/case_builder/llm/README.md`, `src/case_builder/llm/provider.py`
- Modify: `pyproject.toml` (new `llm` extra)
- Test: `tests/test_llm_provider.py`

**Interfaces:**
- Consumes: nothing internal.
- Produces:
  - `parse_model_spec(spec: str) -> tuple[str, str]` — `"ollama:llama3.1"` → `("ollama", "llama3.1")`; raises `ValueError` on missing colon/provider/model.
  - `active_model_spec() -> tuple[str, str]` — parses `CRK_MODEL` env var, defaulting to `DEFAULT_MODEL_SPEC = "ollama:llama3.1"`.
  - `is_local_provider(provider: str) -> bool` — `True` only for `"ollama"`.
  - `get_chat_model(spec: str | None = None)` — resolves the spec (arg > env > default) and returns `init_chat_model(model, model_provider=provider)` from langchain; raises `RuntimeError` with an install hint when langchain is missing.

- [ ] **Step 1: Write the failing test**

Create `tests/test_llm_provider.py`:

```python
import pytest

from case_builder.llm.provider import (
    DEFAULT_MODEL_SPEC,
    active_model_spec,
    is_local_provider,
    parse_model_spec,
)


def test_parse_model_spec_splits_provider_and_model():
    assert parse_model_spec("ollama:llama3.1") == ("ollama", "llama3.1")
    assert parse_model_spec("anthropic:claude-sonnet-5") == ("anthropic", "claude-sonnet-5")


def test_parse_model_spec_rejects_malformed_specs():
    for bad in ("", "ollama", ":model", "provider:"):
        with pytest.raises(ValueError):
            parse_model_spec(bad)


def test_active_model_spec_defaults_local(monkeypatch):
    monkeypatch.delenv("CRK_MODEL", raising=False)

    assert active_model_spec() == parse_model_spec(DEFAULT_MODEL_SPEC)
    assert is_local_provider(active_model_spec()[0]) is True


def test_active_model_spec_reads_env(monkeypatch):
    monkeypatch.setenv("CRK_MODEL", "anthropic:claude-sonnet-5")

    provider, model = active_model_spec()

    assert provider == "anthropic"
    assert is_local_provider(provider) is False


def test_get_chat_model_hints_at_llm_extra_when_langchain_missing(monkeypatch):
    import builtins

    from case_builder.llm import provider as provider_module

    real_import = builtins.__import__

    def block_langchain(name, *args, **kwargs):
        if name.startswith("langchain"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block_langchain)

    with pytest.raises(RuntimeError, match=r"\[llm\]"):
        provider_module.get_chat_model("ollama:llama3.1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <project_root>/ && .venv/bin/python -m pytest tests/test_llm_provider.py -v`
Expected: FAIL with `ModuleNotFoundError` for `case_builder.llm`

- [ ] **Step 3: Write minimal implementation**

Create `src/case_builder/llm/provider.py`:

```python
"""Provider-pluggable chat-model resolution with a local default."""

from __future__ import annotations

import os

DEFAULT_MODEL_SPEC = "ollama:llama3.1"
LOCAL_PROVIDERS = frozenset({"ollama"})


def parse_model_spec(spec: str) -> tuple[str, str]:
    """Split 'provider:model' into its parts, validating both are present."""
    provider, separator, model = (spec or "").partition(":")
    if not separator or not provider.strip() or not model.strip():
        raise ValueError(f"CRK_MODEL must look like 'provider:model' (e.g. '{DEFAULT_MODEL_SPEC}'), got: {spec!r}")
    return provider.strip(), model.strip()


def active_model_spec() -> tuple[str, str]:
    return parse_model_spec(os.environ.get("CRK_MODEL") or DEFAULT_MODEL_SPEC)


def is_local_provider(provider: str) -> bool:
    return provider in LOCAL_PROVIDERS


def get_chat_model(spec: str | None = None):
    """Return a langchain chat model for the requested or configured spec."""
    provider, model = parse_model_spec(spec) if spec else active_model_spec()
    try:
        from langchain.chat_models import init_chat_model
    except ImportError as exc:
        raise RuntimeError(
            "LLM support requires the llm extra. Install with `pip install -e '.[llm]'` "
            "(plus the provider package, e.g. langchain-ollama or langchain-anthropic)."
        ) from exc
    return init_chat_model(model, model_provider=provider)
```

Create `src/case_builder/llm/__init__.py`:

```python
"""Bounded LLM agents and provider resolution for the case builder."""

from __future__ import annotations

from .provider import active_model_spec, get_chat_model, is_local_provider

__all__ = ["active_model_spec", "get_chat_model", "is_local_provider"]
```

Create `src/case_builder/llm/README.md`:

```markdown
# case_builder.llm

Provider resolution and bounded, single-purpose LLM agents. Agents accept any
object with `.invoke(prompt)` returning an object with `.content`, so tests
inject fakes and never require langchain or a running model.

| Module | Responsibility |
| --- | --- |
| `provider.py` | `CRK_MODEL` spec parsing (`provider:model`), local-provider check, `get_chat_model()` via langchain `init_chat_model`. |
| `packet_agent.py` | Fill a CLI-drafted extraction packet from source text: JSON-only output, one retry with error feedback, guilt-label lint, automation defaults, no invented source IDs. |
| `audit_brief.py` | Summarize deterministic audit outputs into a reviewer brief under `staging/candidates/`. Flags, never decides. |
| `lane_suggest.py` | Suggest additional source lanes with rationale; suggestions are recorded, never silently applied. |

Configuration: `CRK_MODEL=provider:model` (default `ollama:llama3.1`).
Non-local providers trigger an `llm_egress` audit row via `ops.policy`.
LLM output is never evidence: agent-written records stay `status: unverified`,
low confidence, `public_export: false`, and go through the packet review gate.
```

Update `pyproject.toml` — add after the `agentic` extra:

```toml
llm = [
  "langchain>=0.3",
  "langchain-ollama>=0.2",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd <project_root>/ && .venv/bin/python -m pytest tests/test_llm_provider.py tests/test_case_builder_structure.py -v`
Expected: PASS (no need to install the `llm` extra — tests never import langchain)

- [ ] **Step 5: Commit**

```bash
git add src/case_builder/llm pyproject.toml tests/test_llm_provider.py
git commit -m "feat(llm): add provider-pluggable chat model layer with local default

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Packet-filling agent

**Files:**
- Create: `src/case_builder/llm/packet_agent.py`
- Test: `tests/test_packet_agent.py`

**Interfaces:**
- Consumes: `ops.policy.lint_guilt_labels(packet) -> list[str]`, `ops.policy.apply_automation_defaults(record) -> dict`.
- Produces:
  - `class PacketAgentError(RuntimeError)`
  - `fill_packet(model, packet: dict, source_text: str, *, source_id: str, max_chars: int = 24000) -> dict` — returns the filled, hardened packet or raises `PacketAgentError` after one retry.
  - `ASSERTION_RECORD_KEYS = ("claims", "events", "relationships", "event_links", "quotes")` — the record lists that receive `apply_automation_defaults`; all other record lists get only `public_export: False`.
  - Module-level `bounded_context(text, max_chars) -> str` (head + tail slice; retrieval-index chunk selection is a documented follow-up).
  - Model contract: `model.invoke(prompt: str)` returns an object whose `.content` (or the object itself, via `str()`) is the response text.

- [ ] **Step 1: Write the failing test**

Create `tests/test_packet_agent.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <project_root>/ && .venv/bin/python -m pytest tests/test_packet_agent.py -v`
Expected: FAIL with `ModuleNotFoundError` for `case_builder.llm.packet_agent`

- [ ] **Step 3: Write minimal implementation**

Create `src/case_builder/llm/packet_agent.py`:

```python
"""Bounded packet-filling agent: one structured-output call plus one retry.

Context is bounded by head+tail truncation; selecting chunks via the local
retrieval index is a follow-up once indexed cases are the norm.
"""

from __future__ import annotations

import json
from typing import Any

from ..ops.policy import apply_automation_defaults, lint_guilt_labels

ASSERTION_RECORD_KEYS = ("claims", "events", "relationships", "event_links", "quotes")
TRUNCATION_MARK = "\n...[truncated]...\n"

PROMPT_TEMPLATE = """You are filling a research extraction packet from one source text.

Rules:
- Output ONLY the completed JSON packet. No prose, no code fences.
- Keep exactly the packet's existing top-level keys. Do not add new ones.
- Every record you add must include "source_ids": ["{source_id}"]. Never cite any other source.
- Record only what the source itself states. Preserve how the source frames it.
- Use neutral role labels (witness, person_mentioned, former_member, official, relative).
  Never label anyone suspect/perpetrator/accomplice/cult member unless the source
  uses that exact wording, and then include "label_source_ids": ["{source_id}"].
- Leave uncertainty visible; do not resolve contradictions.

Packet template:
{packet_json}

Source text:
{source_text}
"""

RETRY_TEMPLATE = """Your previous packet was rejected for these reasons:
{problems}

Fix every problem and output ONLY the corrected JSON packet.

{original_prompt}"""


class PacketAgentError(RuntimeError):
    """Raised when the model cannot produce a valid packet within one retry."""


def fill_packet(model: Any, packet: dict[str, Any], source_text: str, *, source_id: str, max_chars: int = 24000) -> dict[str, Any]:
    prompt = PROMPT_TEMPLATE.format(
        source_id=source_id,
        packet_json=json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
        source_text=bounded_context(source_text, max_chars),
    )
    problems: list[str] = []
    for attempt in range(2):
        request = prompt if attempt == 0 else RETRY_TEMPLATE.format(problems="\n".join(problems), original_prompt=prompt)
        reply = model.invoke(request)
        content = str(getattr(reply, "content", reply))
        try:
            filled = parse_json_response(content)
        except ValueError as exc:
            problems = [str(exc)]
            continue
        problems = validate_filled_packet(packet, filled, source_id)
        if not problems:
            return harden_records(filled)
    raise PacketAgentError("; ".join(problems))


def parse_json_response(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"The response was not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("The response must be a JSON object matching the packet template.")
    return parsed


def validate_filled_packet(template: dict[str, Any], filled: dict[str, Any], source_id: str) -> list[str]:
    problems = [f"Unknown top-level key: {key}" for key in filled if key not in template]
    for key, value in filled.items():
        if not isinstance(value, list):
            continue
        for index, record in enumerate(value):
            if isinstance(record, dict) and source_id not in (record.get("source_ids") or []):
                problems.append(f"{key}[{index}] must cite source_ids ['{source_id}']; never invent source IDs")
    lint = lint_guilt_labels(filled)
    problems.extend(f"guilt-label lint: {item}" for item in lint)
    return problems


def harden_records(filled: dict[str, Any]) -> dict[str, Any]:
    hardened: dict[str, Any] = {}
    for key, value in filled.items():
        if isinstance(value, list) and key in ASSERTION_RECORD_KEYS:
            hardened[key] = [apply_automation_defaults(record) if isinstance(record, dict) else record for record in value]
        elif isinstance(value, list):
            hardened[key] = [
                {**record, "public_export": False} if isinstance(record, dict) else record for record in value
            ]
        else:
            hardened[key] = value
    return hardened


def bounded_context(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    head = text[: max_chars * 2 // 3]
    tail = text[-(max_chars - len(head)) :]
    return head + TRUNCATION_MARK + tail
```

Note: `bounded_context` output slightly exceeds `max_chars` by the truncation
marker length — the test allows for this. If the `test_bounded_context_keeps_head_and_tail`
assertion fails on boundary math, adjust the head/tail split, not the test.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd <project_root>/ && .venv/bin/python -m pytest tests/test_packet_agent.py tests/test_case_builder_structure.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add src/case_builder/llm/packet_agent.py tests/test_packet_agent.py
git commit -m "feat(llm): add bounded packet-filling agent with lint and retry

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Lane suggestions + readiness brief helpers

**Files:**
- Create: `src/case_builder/llm/lane_suggest.py`
- Create: `src/case_builder/llm/audit_brief.py`
- Test: `tests/test_llm_helpers.py`

**Interfaces:**
- Consumes: `agents.source_lanes.LANE_TRIGGERS` (dict of known lane names), `ops.policy.ensure_staged_write / PolicyError`, `casefile.ensure_case / log_action`; the Task 3 model contract (`.invoke` → `.content`).
- Produces:
  - `lane_suggest.suggest_lanes(model, subject: str, current_lanes: Sequence[str]) -> list[dict]` — each item `{"lane": <known lane not already selected>, "rationale": str}`; unknown or duplicate lanes are silently dropped; malformed model output returns `[]` (suggestions are optional, never fatal).
  - `audit_brief.write_readiness_brief(model, case_dir: str, audit_results: Sequence[dict]) -> str` — writes `staging/candidates/readiness_brief_<YYYYMMDD>.md`, logs a `readiness_brief` research action, returns the path.

- [ ] **Step 1: Write the failing test**

Create `tests/test_llm_helpers.py`:

```python
import json

from case_builder.llm.audit_brief import write_readiness_brief
from case_builder.llm.lane_suggest import suggest_lanes


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
    assert "flags issues for a human reviewer" in content  # framing header
    actions = (synthetic_case_copy / "records" / "research_actions.jsonl").read_text(encoding="utf-8")
    assert "readiness_brief" in actions
    # Audit stdout made it into the prompt:
    assert "1 flag" in model.prompts[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <project_root>/ && .venv/bin/python -m pytest tests/test_llm_helpers.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `src/case_builder/llm/lane_suggest.py`:

```python
"""Optional LLM lane suggestions — recorded with rationale, never auto-applied."""

from __future__ import annotations

import json
from typing import Any, Sequence

from ..agents.source_lanes import LANE_TRIGGERS

PROMPT_TEMPLATE = """Given this research subject, suggest additional public-record
source lanes worth planning. Choose only from this list:
{lanes}

Already selected: {current}

Subject: {subject}

Output ONLY a JSON array of objects: [{{"lane": "<name>", "rationale": "<one sentence>"}}]
Suggest at most 3. Output [] if nothing else applies.
"""


def suggest_lanes(model: Any, subject: str, current_lanes: Sequence[str]) -> list[dict[str, str]]:
    prompt = PROMPT_TEMPLATE.format(
        lanes=", ".join(sorted(LANE_TRIGGERS)),
        current=", ".join(current_lanes) or "none",
        subject=subject,
    )
    reply = model.invoke(prompt)
    content = str(getattr(reply, "content", reply)).strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    suggestions: list[dict[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        lane = item.get("lane")
        if lane in LANE_TRIGGERS and lane not in current_lanes:
            suggestions.append({"lane": str(lane), "rationale": str(item.get("rationale") or "")})
    return suggestions
```

Create `src/case_builder/llm/audit_brief.py`:

```python
"""Reviewer brief over deterministic audit outputs. Flags, never decides."""

from __future__ import annotations

import datetime as dt
from typing import Any, Sequence

from ..casefile import ensure_case, log_action
from ..ops.policy import ensure_staged_write

PROMPT_TEMPLATE = """Summarize these public-readiness audit outputs for a human reviewer.
List concrete blockers and open questions as short bullet points. Do NOT decide
whether the case is ready and do NOT soften findings.

{audits}
"""

HEADER = (
    "# Readiness review brief\n\n"
    "This brief flags issues for a human reviewer. It is not evidence and it\n"
    "does not decide readiness; the deterministic audit outputs remain the\n"
    "source of record.\n\n"
)


def write_readiness_brief(model: Any, case_dir: str, audit_results: Sequence[dict[str, Any]]) -> str:
    case = ensure_case(case_dir)
    audits = "\n\n".join(f"## {item.get('name')}\n{item.get('stdout') or '(no output)'}" for item in audit_results)
    reply = model.invoke(PROMPT_TEMPLATE.format(audits=audits))
    body = str(getattr(reply, "content", reply)).strip()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    target = case / "staging" / "candidates" / f"readiness_brief_{stamp}.md"
    ensure_staged_write(case, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(HEADER + body + "\n", encoding="utf-8")
    log_action(case, "readiness_brief", {"path": str(target.name), "audits": [str(item.get("name")) for item in audit_results]})
    return str(target)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd <project_root>/ && .venv/bin/python -m pytest tests/test_llm_helpers.py tests/test_case_builder_structure.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/case_builder/llm/lane_suggest.py src/case_builder/llm/audit_brief.py tests/test_llm_helpers.py
git commit -m "feat(llm): add lane suggestion and readiness brief helpers

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: LLM graph nodes + pipeline wiring

**Files:**
- Create: `src/case_builder/graph/llm_nodes.py`
- Modify: `src/case_builder/graph/runner.py` (thread `model_factory` through)
- Modify: `src/case_builder/graph/state.py` and `src/case_builder/models/state.py` (add `llm_enabled: bool`, `lane_suggestions: list[dict]`)
- Test: `tests/test_llm_nodes.py`

**Interfaces:**
- Consumes: Tasks 1–4 functions; `graph.pipeline_nodes.merge_results`, `graph.nodes.required_case_dir`; `ops.extraction.read_packet / save_packet`; `ops.query.get_source_text`; `llm.provider.active_model_spec / is_local_provider`; `ops.policy.record_llm_egress`.
- Produces:
  - Node factories `suggest_lanes_node(runner, model_factory)`, `fill_packets_node(runner, model_factory)`, `readiness_brief_node(runner, model_factory)` — every one skips (returning `{"status": "<name>_skipped"}`) unless `state["llm_enabled"]` is truthy, `model_factory` is not `None`, and `runner.dry_run` is `False`.
  - `pipeline_nodes_list(runner, *, use_interrupt, model_factory=None)` — inserts `suggest_lanes` after `infer_lanes`, `fill_packets` after `draft_packets`, `readiness_brief` after `readiness_audit`.
  - `run_sequential(state, runner, *, model_factory=None)` and `build_case_builder_graph(runner, *, checkpointer=None, use_interrupt=False, model_factory=None)`.
  - Status vocabulary: `lane_suggestions_skipped`, `lanes_suggested`, `fill_skipped`, `packets_filled`, `brief_skipped`, `readiness_brief_written`.
  - `model_factory` contract: zero-argument callable returning a model satisfying the Task 3 contract.

- [ ] **Step 1: Write the failing test**

Create `tests/test_llm_nodes.py`:

```python
import json
from pathlib import Path

from case_builder.graph.llm_nodes import (
    fill_packets_node,
    readiness_brief_node,
    suggest_lanes_node,
)
from case_builder.ops.runner import CrkRunner

KIT_ROOT = Path(__file__).resolve().parents[1]


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
    # Stage a template packet and a text source it refers to.
    source_id = "SDEMO0001"
    text_file = synthetic_case_copy / "raw" / "sources" / f"{source_id}.txt"
    text_file.parent.mkdir(parents=True, exist_ok=True)
    text_file.write_text("A search occurred near the river.", encoding="utf-8")
    sources_path = synthetic_case_copy / "records" / "sources.jsonl"
    rows = [json.loads(line) for line in sources_path.read_text(encoding="utf-8").splitlines()]
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
    (packet_dir / "SDEMO0001_extraction.json").write_text(json.dumps({"source_id": "SDEMO0001", "claims": []}), encoding="utf-8")

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <project_root>/ && .venv/bin/python -m pytest tests/test_llm_nodes.py -v`
Expected: FAIL with `ModuleNotFoundError` for `case_builder.graph.llm_nodes`

- [ ] **Step 3: Write the nodes**

Create `src/case_builder/graph/llm_nodes.py`:

```python
"""Optional LLM agent nodes. Every node skips unless llm_enabled, a model
factory is provided, and the runner is executing (not dry-run)."""

from __future__ import annotations

from typing import Any, Callable

from ..llm.audit_brief import write_readiness_brief
from ..llm.lane_suggest import suggest_lanes
from ..llm.packet_agent import PacketAgentError, fill_packet
from ..llm.provider import active_model_spec, is_local_provider
from ..ops import extraction as extraction_ops
from ..ops import query as query_ops
from ..ops.policy import record_llm_egress
from .nodes import required_case_dir
from .state import GraphState

ModelFactory = Callable[[], Any]
AUDIT_NAMES = {
    "audit_contradictions",
    "review_narrative_readiness",
    "audit_privacy_redactions",
    "audit_source_independence",
}


def llm_active(state: GraphState, runner, model_factory: ModelFactory | None) -> bool:
    return bool(state.get("llm_enabled")) and model_factory is not None and not runner.dry_run


def note_egress(case_dir: str, context: str) -> None:
    provider, _model = active_model_spec()
    if not is_local_provider(provider):
        record_llm_egress(case_dir, provider, context)


def suggest_lanes_node(runner, model_factory: ModelFactory | None):
    def node(state: GraphState) -> GraphState:
        if not llm_active(state, runner, model_factory):
            return {"status": "lane_suggestions_skipped"}
        suggestions = suggest_lanes(model_factory(), state.get("subject") or "", state.get("lanes") or [])
        return {"lane_suggestions": suggestions, "status": "lanes_suggested"}

    return node


def fill_packets_node(runner, model_factory: ModelFactory | None):
    def node(state: GraphState) -> GraphState:
        if not llm_active(state, runner, model_factory):
            return {"status": "fill_skipped"}
        case_dir = required_case_dir(state)
        model = model_factory()
        errors = list(state.get("errors") or [])
        filled_count = 0
        for name in state.get("packets") or []:
            packet_result = extraction_ops.read_packet(case_dir, name)
            if not packet_result.ok:
                errors.extend(packet_result.errors)
                continue
            packet = packet_result.data["packet"]
            source_id = str(packet.get("source_id") or name.split("_extraction")[0])
            text_result = query_ops.get_source_text(case_dir, source_id, include_private=True)
            if not text_result.ok:
                errors.extend(text_result.errors)
                continue
            note_egress(case_dir, f"fill_packets:{source_id}")
            try:
                filled = fill_packet(model, packet, text_result.data["text"], source_id=source_id)
            except PacketAgentError as exc:
                errors.append(f"fill_packets {name}: {exc}")
                continue
            saved = extraction_ops.save_packet(case_dir, name, filled)
            if not saved.ok:
                errors.extend(saved.errors)
                continue
            filled_count += 1
        return {
            "errors": errors,
            "status": "packets_filled" if filled_count or not errors else "error",
        }

    return node


def readiness_brief_node(runner, model_factory: ModelFactory | None):
    def node(state: GraphState) -> GraphState:
        if not llm_active(state, runner, model_factory):
            return {"status": "brief_skipped"}
        case_dir = required_case_dir(state)
        audit_results = [item for item in (state.get("tool_results") or []) if item.get("name") in AUDIT_NAMES]
        note_egress(case_dir, "readiness_brief")
        path = write_readiness_brief(model_factory(), case_dir, audit_results)
        return {
            "tool_results": [*(state.get("tool_results") or []), {"name": "readiness_brief", "ok": True, "data": {"path": path}}],
            "status": "readiness_brief_written",
        }

    return node
```

- [ ] **Step 4: Wire into state and runner**

In `src/case_builder/models/state.py`, add two fields to `CaseBuilderState` (after `index_enabled`):

```python
    llm_enabled: bool = False
    lane_suggestions: list[dict[str, Any]] = field(default_factory=list)
```

In `src/case_builder/graph/state.py`, add to `GraphState` (after `index_enabled`):

```python
    llm_enabled: bool
    lane_suggestions: list[dict[str, Any]]
```

In `src/case_builder/graph/runner.py`:

1. Add the import:

```python
from .llm_nodes import fill_packets_node, readiness_brief_node, suggest_lanes_node
```

2. Replace `pipeline_nodes_list` with:

```python
def pipeline_nodes_list(runner: CrkRunner, *, use_interrupt: bool, model_factory=None):
    return [
        ("infer_lanes", infer_lanes_node),
        ("suggest_lanes", suggest_lanes_node(runner, model_factory)),
        ("init_case", init_case_node(runner)),
        ("plan_public_records", plan_public_records_node(runner)),
        ("source_capture", source_capture_node(runner)),
        ("parse_or_ocr", parse_or_ocr_node(runner)),
        ("draft_packets", draft_packets_node(runner)),
        ("fill_packets", fill_packets_node(runner, model_factory)),
        ("packet_review_gate", packet_review_gate_node(use_interrupt)),
        ("import_and_validate", import_and_validate_node(runner)),
        ("index_case", index_case_node(runner)),
        ("readiness_audit", readiness_audit_node(runner)),
        ("readiness_brief", readiness_brief_node(runner, model_factory)),
        ("export_review_gate", export_review_gate_node(use_interrupt)),
        ("export_bundle", export_bundle_node(runner)),
    ]
```

3. Update the two callers to accept and forward the factory:

```python
def run_sequential(state: CaseBuilderState, runner: CrkRunner, *, model_factory=None) -> dict[str, object]:
    current: GraphState = state.to_dict()
    for _name, node in pipeline_nodes_list(runner, use_interrupt=False, model_factory=model_factory):
        current.update(node(current))
        if current.get("status") in STOP_STATUSES:
            break
    current["runner"] = "sequential"
    return dict(current)


def build_case_builder_graph(runner: CrkRunner, *, checkpointer=None, use_interrupt: bool = False, model_factory=None):
```

(and inside `build_case_builder_graph`, pass `model_factory=model_factory` to `pipeline_nodes_list`).

- [ ] **Step 5: Run tests to verify pass, including Phase 2 canaries**

Run: `cd <project_root>/ && .venv/bin/python -m pytest tests/test_llm_nodes.py tests/test_pipeline_runner.py tests/test_case_builder.py tests/test_langgraph_resume.py -v`
Expected: PASS — the canaries are unaffected because both new nodes return only a skip status in dry runs / without a factory, and Phase 2's `test_sequential_full_pass...` asserts `planned_commands` (which skip statuses never touch).

Note: the full-pass test asserts the exact planned-command sequence, not statuses between nodes, so inserting skipping nodes is invisible to it. If any canary fails, fix the node skip conditions — do not touch the canary.

- [ ] **Step 6: Commit**

```bash
git add src/case_builder/graph/llm_nodes.py src/case_builder/graph/runner.py src/case_builder/graph/state.py src/case_builder/models/state.py tests/test_llm_nodes.py
git commit -m "feat(graph): wire optional LLM agent nodes into the pipeline

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Service/CLI flag, docs, final sweep

**Files:**
- Modify: `src/case_builder/app/service.py` (model factory selection)
- Modify: `src/case_builder/cli.py` (plan `--llm` flag)
- Modify: `docs/case-builder-langgraph.md`, `src/case_builder/graph/README.md`
- Test: `tests/test_service_resume.py` (append one test)

**Interfaces:**
- Consumes: `llm.provider.get_chat_model`, Task 5 signatures.
- Produces: `run_case_builder(state, *, execute=False, runner="auto", checkpoint=False)` unchanged signature — it derives the factory from `state.llm_enabled` (factory is `get_chat_model` when enabled, else `None`) and forwards `model_factory=` to `run_sequential` / `build_case_builder_graph`. `resume_case_builder` gains `llm: bool = False` parameter doing the same. CLI `plan` and `resume` gain `--llm`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_service_resume.py`:

```python
def test_plan_parser_accepts_llm_flag():
    parser = build_parser()

    args = parser.parse_args(["plan", "data/cases/x", "--llm"])

    assert args.llm is True


def test_llm_disabled_state_never_builds_a_model(monkeypatch):
    from case_builder.app import service
    from case_builder.models.state import CaseBuilderState

    def explode():
        raise AssertionError("model factory must not be constructed when llm is disabled")

    monkeypatch.setattr(service, "_model_factory", lambda enabled: explode() if enabled else None)

    result = service.run_case_builder(CaseBuilderState(case_dir="data/cases/x", subject="s"), runner="sequential")

    assert result["status"] == "waiting_for_human_review"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <project_root>/ && .venv/bin/python -m pytest tests/test_service_resume.py -v`
Expected: FAIL — `--llm` unrecognized; `service._model_factory` missing

- [ ] **Step 3: Update service and CLI**

In `src/case_builder/app/service.py`:

1. Add helper (before `run_case_builder`):

```python
def _model_factory(llm_enabled: bool):
    if not llm_enabled:
        return None
    from ..llm.provider import get_chat_model

    return get_chat_model
```

2. In `run_case_builder`, after `crk = CrkRunner(...)`, add:

```python
    model_factory = _model_factory(state.llm_enabled)
```

and forward it in all three call sites:

```python
        return run_sequential(state, crk, model_factory=model_factory)
...
        graph = build_case_builder_graph(crk, model_factory=model_factory)
...
    graph = build_case_builder_graph(
        crk, checkpointer=case_checkpointer(state.case_dir), use_interrupt=True, model_factory=model_factory
    )
```

3. In `resume_case_builder`, add parameter `llm: bool = False` and build the graph with `model_factory=_model_factory(llm)`:

```python
    graph = build_case_builder_graph(
        crk, checkpointer=case_checkpointer(case_dir), use_interrupt=True, model_factory=_model_factory(llm)
    )
```

In `src/case_builder/cli.py`:

1. Add to the `plan` subparser (after `--thread`):

```python
    plan.add_argument("--llm", action="store_true", help="Enable LLM agent nodes (CRK_MODEL, default ollama:llama3.1).")
```

2. Add to the `resume` subparser (after `--execute`):

```python
    resume.add_argument("--llm", action="store_true", help="Enable LLM agent nodes on the resumed run.")
```

3. In `run_plan_command`, add `llm_enabled=args.llm` to the `CaseBuilderState(...)` construction; in `run_resume_command`, pass `llm=args.llm` to `resume_case_builder(...)`.

- [ ] **Step 4: Update docs**

In `docs/case-builder-langgraph.md`, replace the "Next Nodes (Phase 3)" section with:

```markdown
## LLM Agent Nodes

Optional nodes activate with `--llm` (plus `--execute`) and the `CRK_MODEL`
environment variable (`provider:model`, default `ollama:llama3.1`; install
`pip install -e '.[llm]'` plus the provider package):

- `suggest_lanes`: lane suggestions with rationale, recorded in
  `lane_suggestions` — never silently applied.
- `fill_packets`: fills CLI-drafted extraction packets from parsed source
  text. Output must be JSON matching the template, cite only the packet's
  source ID, and pass the guilt-label lint; assertion records are forced to
  `status: unverified`, capped confidence, `public_export: false`. One retry
  with error feedback, then the failure is recorded and the packet is left
  unfilled for a human.
- `readiness_brief`: summarizes the deterministic audit outputs into
  `staging/candidates/readiness_brief_<date>.md`. It flags; it never decides.

Non-local providers are recorded as `llm_egress` rows in
`research_actions.jsonl` because source text leaves the machine. LLM output
is never evidence; filled packets still stop at the packet review gate.
```

In `src/case_builder/graph/README.md`, add a row to the module table:

```markdown
| `llm_nodes.py` | Optional LLM agent nodes (lane suggestions, packet filling, readiness brief); skip unless `--llm` + execute + model factory. |
```

- [ ] **Step 5: Run the full suite and sweep**

```bash
cd <project_root>/
.venv/bin/python -m compileall -q src
.venv/bin/python -m pytest -q
.venv/bin/python -m case_builder.cli plan data/cases/example_case --subject "missing person map" 2>/dev/null | grep '"status"'
```

Expected: compileall silent; full suite green; CLI prints `"status": "waiting_for_human_review"`.

- [ ] **Step 6: Commit**

```bash
git add src/case_builder/app/service.py src/case_builder/cli.py docs/case-builder-langgraph.md src/case_builder/graph/README.md tests/test_service_resume.py
git commit -m "feat(app): add --llm flag and document the agent nodes

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Self-Review Notes

- **Spec coverage (Phase 3 bullets):** `llm/` provider with `CRK_MODEL` and local default → Task 2; egress tagging in ops.policy → Task 1 (recorded by nodes in Task 5); `draft_extraction` agent with schema-shaped output, unverified status, no invented source IDs, one retry → Task 3 + `fill_packets` node in Task 5; `readiness_audit` LLM brief that flags-never-decides → Task 4 + Task 5; `lane_router` suggestions with rationale, never silently applied → Task 4 + Task 5. Spec's "chunked via the retrieval index when long" is downgraded to bounded head+tail context with the retrieval upgrade documented in the module docstring (Task 3) — deliberate YAGNI deviation, noted here.
- **Type consistency:** the model contract (`.invoke(str)` → `.content`) is identical across Tasks 3, 4, 5; `model_factory` is a zero-arg callable everywhere; skip-status names in Task 5's tests match the node implementations; `get_source_text` signature in Task 1 matches its use in Task 5.
- **Safety:** filled packets are saved via `ops.extraction.save_packet`, which re-runs the guilt-label lint and staged-write policy from Phase 1 — the agent cannot bypass ops enforcement even if `harden_records` regressed.
