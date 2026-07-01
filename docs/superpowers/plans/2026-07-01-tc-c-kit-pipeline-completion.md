# tc-c-kit Pipeline Completion (Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Grow the case-builder graph from the 4-node bootstrap to the full deterministic case-building loop with a SQLite checkpointer and resumable interrupt-based review gates.

**Architecture:** Seven new deterministic nodes (`source_capture`, `parse_or_ocr`, `draft_packets`, `import_and_validate`, `index_case`, `readiness_audit`, `export_bundle`) plus two gate nodes call the Phase 1 ops core exclusively. Gates use LangGraph `interrupt()` when a checkpointer is active and degrade to a terminal `waiting_for_human_review` status in the sequential runner and non-checkpointed graphs (conditional edges route waiting states to END). A `SqliteSaver` at `<case>/.runs/checkpoints.db` makes runs survive restarts; `trcr-case-builder resume` continues a paused thread with packet approvals/rejections and export approval.

**Tech Stack:** Python ≥3.10, LangGraph (`langgraph`, `langgraph-checkpoint-sqlite` — added to the existing `[agentic]` extra), pytest with `importorskip` so the suite stays green without the extra installed.

## Global Constraints

- All paths relative to the repo root `/home/jdean/Documents/programming/true-crime-research/tc-c-kit` (the kit is now a self-contained git repo; `.agents/`, `src/`, `tests/`, `docs/`, `data/` all live here). `REPO_ROOT` in test snippets is the kit root (`parents[1]` from a test file), which is also the `TrcrRunner` repo root — `tcr.py` resolves to `.agents/skills/truecrime-cult-research/scripts/tcr.py` inside it.
- Every Python module stays under **200 non-comment LOC**; every package dir under `src/case_builder/` has a `README.md` (enforced by `tests/test_case_builder_structure.py`).
- `[project] dependencies = []` stays empty — LangGraph additions go in the `agentic` optional extra only.
- Nodes call **ops functions only** — never `tcr.py`, ledger files, or local-stack modules directly (spec: single safety-enforcement point).
- `import_extraction` is called with `confirm=True` **only** downstream of a review gate (human approval flows through the gate).
- Run tests with: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest <path> -v` (baseline: 79 passed).
- Behavior preservation: `tests/test_case_builder.py` (sequential dry run stops at the packet gate with `status="waiting_for_human_review"`, `tool_results` names `["init_case", "plan_public_records"]`) must pass **unmodified**.
- LangGraph-dependent tests start with `pytest.importorskip("langgraph")` so the suite passes with or without the extra.
- Commit after every task, conventional-commit style, ending with:

  ```
  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```

## Existing interfaces this plan builds on (Phase 1, already landed)

- `case_builder.ops.runner.TrcrRunner(*, repo_root=None, dry_run=True, python_executable=None)` — `.run(name, args) -> OpResult`, `.dry_run: bool`.
- `case_builder.ops.result.OpResult` — `.ok`, `.errors: list[str]`, `.command: list[str]`, `.to_dict()`.
- `ops.case.init_case(runner, case_dir, title=None)`, `ops.case.validate(runner, case_dir)`, `ops.case.report(runner, case_dir)`.
- `ops.sources.plan_public_records(runner, case_dir, subject, lanes)`, `ops.sources.ingest_url(runner, case_dir, url, *, title=None, source_type=None, reliability_grade=None, timeout=None, public_export=True)`, `ops.sources.parse_source(case_dir, source_id, *, force=False)`, `ops.sources.ocr_source(case_dir, source_id, *, language="eng", force=False)` — the last two are local ops that may raise `RuntimeError` when Docling/OCRmyPDF are missing.
- `ops.extraction.draft_extraction(runner, case_dir, source_id, *, template="generic")`, `ops.extraction.list_packets(case_dir)` (`data={"packets": [...]}`), `ops.extraction.import_extraction(runner, case_dir, packet_path, *, confirm=False)`.
- `ops.query.get_records(case_dir, record_type, *, include_private=False)` (`data={"records": [...], ...}`), `ops.query.index_case(case_dir, *, include_private=False, ...)` — may raise on missing retrieval deps.
- `ops.review.audit_contradictions / review_narrative_readiness / audit_privacy_redactions / audit_source_independence(runner, case_dir)`.
- `ops.exports.export_manim(runner, case_dir, *, include_private=False)`.
- `graph.nodes.infer_lanes_node`, `init_case_node(runner)`, `plan_public_records_node(runner)`, `merge_result(state, result, success_status)`, `required_case_dir(state)`, `append_error(state, message)`.
- `models.state.CaseBuilderState` dataclass with `.to_dict()/.from_dict()/.normalized()`.

## File Structure (end state)

```
src/case_builder/graph/
  state.py           # MODIFIED: new GraphState keys
  nodes.py           # unchanged (bootstrap nodes + merge helpers)
  gates.py           # NEW: packet_review_gate_node, export_review_gate_node
  pipeline_nodes.py  # NEW: 7 deterministic pipeline nodes + merge_results
  checkpoint.py      # NEW: case_checkpointer(case_dir) -> SqliteSaver
  runner.py          # MODIFIED: full pipeline list, conditional gate edges, checkpointer param
src/case_builder/models/state.py   # MODIFIED: new CaseBuilderState fields
src/case_builder/app/service.py    # MODIFIED: checkpoint wiring + resume_case_builder
src/case_builder/cli.py            # MODIFIED: plan flags + resume subcommand
pyproject.toml                     # MODIFIED: agentic extra gains langgraph-checkpoint-sqlite
docs/case-builder-langgraph.md     # MODIFIED: workflow + resume docs
src/case_builder/graph/README.md   # MODIFIED: new module rows

New tests:
tests/test_pipeline_state.py
tests/test_pipeline_gates.py
tests/test_pipeline_nodes.py
tests/test_pipeline_runner.py
tests/test_langgraph_resume.py
tests/test_service_resume.py
```

Deliberately out of scope (Phase 3+): LLM packet filling (`draft_packets` stays a deterministic `tcr.py` template call), LLM readiness brief (the `readiness_audit` node runs deterministic audits only), lane-router LLM suggestions, MCP server.

---

### Task 1: Agentic dependencies + state model extensions

**Files:**
- Modify: `pyproject.toml` (agentic extra)
- Modify: `src/case_builder/models/state.py`
- Modify: `src/case_builder/graph/state.py`
- Test: `tests/test_pipeline_state.py`

**Interfaces:**
- Consumes: existing `CaseBuilderState`, `GraphState`.
- Produces: `CaseBuilderState` gains fields `source_urls: list[str]`, `source_ids: list[str]`, `packets: list[str]`, `approved_packets: list[str]`, `rejected_packets: list[dict]`, `export_approved: bool = False`, `index_enabled: bool = False`, `thread_id: str | None = None`; `normalized()` defaults `thread_id` to `run_id`. `GraphState` gains the same keys. `pip install -e '.[agentic]'` now brings `langgraph` + `langgraph-checkpoint-sqlite` + `langsmith`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_pipeline_state.py`:

```python
from case_builder.models.state import CaseBuilderState


def test_state_defaults_new_pipeline_fields():
    state = CaseBuilderState(case_dir="data/cases/x").normalized()

    assert state.source_urls == []
    assert state.source_ids == []
    assert state.packets == []
    assert state.approved_packets == []
    assert state.rejected_packets == []
    assert state.export_approved is False
    assert state.index_enabled is False


def test_thread_id_defaults_to_run_id():
    state = CaseBuilderState(case_dir="data/cases/x").normalized()

    assert state.thread_id == state.run_id


def test_explicit_thread_id_is_kept():
    state = CaseBuilderState(case_dir="data/cases/x", thread_id="thread-7").normalized()

    assert state.thread_id == "thread-7"


def test_round_trip_preserves_pipeline_fields():
    state = CaseBuilderState(
        case_dir="data/cases/x",
        source_urls=["https://example.com/a"],
        approved_packets=["S1_extraction.json"],
        export_approved=True,
        index_enabled=True,
    )

    clone = CaseBuilderState.from_dict(state.to_dict())

    assert clone.source_urls == ["https://example.com/a"]
    assert clone.approved_packets == ["S1_extraction.json"]
    assert clone.export_approved is True
    assert clone.index_enabled is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_pipeline_state.py -v`
Expected: FAIL with `TypeError: CaseBuilderState.__init__() got an unexpected keyword argument 'source_urls'` (or attribute errors)

- [ ] **Step 3: Extend the models**

In `src/case_builder/models/state.py`, replace the `CaseBuilderState` dataclass field block and `normalized()` with:

```python
@dataclass
class CaseBuilderState:
    """Serializable state passed between case-builder workflow steps."""

    case_dir: str
    title: str | None = None
    subject: str | None = None
    run_id: str | None = None
    thread_id: str | None = None
    lanes: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    packets: list[str] = field(default_factory=list)
    approved_packets: list[str] = field(default_factory=list)
    rejected_packets: list[dict[str, Any]] = field(default_factory=list)
    export_approved: bool = False
    index_enabled: bool = False
    planned_commands: list[list[str]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    review_required: bool = True
    status: str = "initialized"
    errors: list[str] = field(default_factory=list)
    runner: str = "sequential"

    def normalized(self) -> "CaseBuilderState":
        if not self.run_id:
            self.run_id = new_run_id(self.case_dir, self.subject)
        if not self.thread_id:
            self.thread_id = self.run_id
        self.lanes = dedupe(self.lanes)
        return self
```

(`to_dict`, `from_dict`, `dedupe`, `new_run_id` stay unchanged.)

In `src/case_builder/graph/state.py`, replace `GraphState` with:

```python
class GraphState(TypedDict, total=False):
    case_dir: str
    title: str | None
    subject: str | None
    run_id: str | None
    thread_id: str | None
    lanes: list[str]
    source_urls: list[str]
    source_ids: list[str]
    packets: list[str]
    approved_packets: list[str]
    rejected_packets: list[dict[str, Any]]
    export_approved: bool
    index_enabled: bool
    planned_commands: list[list[str]]
    tool_results: list[dict[str, Any]]
    review_required: bool
    status: str
    errors: list[str]
    runner: str
```

In `pyproject.toml`, replace the `agentic` extra with:

```toml
agentic = [
  "langgraph",
  "langgraph-checkpoint-sqlite",
  "langsmith",
]
```

- [ ] **Step 4: Install the agentic extra into the venv**

```bash
cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/pip install -e '.[agentic]' -q && .venv/bin/python -c "from langgraph.checkpoint.sqlite import SqliteSaver; from langgraph.types import Command, interrupt; print('agentic stack OK')"
```

Expected: `agentic stack OK`

- [ ] **Step 5: Run tests to verify pass (including full-suite regression)**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_pipeline_state.py -v && .venv/bin/python -m pytest -q`
Expected: new tests PASS; full suite PASS. Note: with langgraph now installed, `run_case_builder(..., runner="auto")` takes the langgraph path — `tests/test_case_builder.py` pins `runner="sequential"`, so it is unaffected.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/case_builder/models/state.py src/case_builder/graph/state.py tests/test_pipeline_state.py
git commit -m "feat(graph): extend run state for pipeline, approvals, and threads

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Review gate nodes

**Files:**
- Create: `src/case_builder/graph/gates.py`
- Test: `tests/test_pipeline_gates.py`

**Interfaces:**
- Consumes: `GraphState` keys from Task 1.
- Produces: `packet_review_gate_node(use_interrupt: bool)` and `export_review_gate_node(use_interrupt: bool)` — node factories returning `Callable[[GraphState], GraphState]`. Behavior contract used by the runner (Task 5): with `use_interrupt=False`, a gate without prior approval returns `{"review_required": True, "status": "waiting_for_human_review"}`; with prior approval in state (`approved_packets` non-empty / `export_approved` truthy) it returns `status="packets_approved"` / `status="export_approved"` and `review_required=False`. With `use_interrupt=True` it calls `langgraph.types.interrupt(payload)` and maps the resume payload keys `approved_packets`, `rejected_packets`, `export_approved` into state.

- [ ] **Step 1: Write the failing test**

Create `tests/test_pipeline_gates.py`:

```python
from case_builder.graph.gates import export_review_gate_node, packet_review_gate_node


def test_packet_gate_waits_without_approvals():
    gate = packet_review_gate_node(use_interrupt=False)

    update = gate({"case_dir": "data/cases/x", "packets": ["S1_extraction.json"]})

    assert update["status"] == "waiting_for_human_review"
    assert update["review_required"] is True


def test_packet_gate_passes_with_prior_approvals():
    gate = packet_review_gate_node(use_interrupt=False)

    update = gate({"case_dir": "data/cases/x", "approved_packets": ["S1_extraction.json"]})

    assert update["status"] == "packets_approved"
    assert update["review_required"] is False


def test_export_gate_waits_without_approval():
    gate = export_review_gate_node(use_interrupt=False)

    update = gate({"case_dir": "data/cases/x"})

    assert update["status"] == "waiting_for_human_review"
    assert update["review_required"] is True


def test_export_gate_passes_when_approved():
    gate = export_review_gate_node(use_interrupt=False)

    update = gate({"case_dir": "data/cases/x", "export_approved": True})

    assert update["status"] == "export_approved"
    assert update["review_required"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_pipeline_gates.py -v`
Expected: FAIL with `ModuleNotFoundError` for `case_builder.graph.gates`

- [ ] **Step 3: Write minimal implementation**

Create `src/case_builder/graph/gates.py`:

```python
"""Human review gates: interrupt-based under LangGraph, terminal otherwise."""

from __future__ import annotations

from .state import GraphState

WAITING = {"review_required": True, "status": "waiting_for_human_review"}


def packet_review_gate_node(use_interrupt: bool):
    def node(state: GraphState) -> GraphState:
        if state.get("approved_packets"):
            return {"status": "packets_approved", "review_required": False}
        if use_interrupt:
            from langgraph.types import interrupt

            decision = interrupt(
                {
                    "action": "review_packets",
                    "case_dir": state.get("case_dir"),
                    "packets": state.get("packets") or [],
                }
            )
            approved = list(decision.get("approved_packets") or [])
            return {
                "approved_packets": approved,
                "rejected_packets": list(decision.get("rejected_packets") or []),
                "review_required": False,
                "status": "packets_approved" if approved else "packets_rejected",
            }
        return dict(WAITING)

    return node


def export_review_gate_node(use_interrupt: bool):
    def node(state: GraphState) -> GraphState:
        if state.get("export_approved"):
            return {"status": "export_approved", "review_required": False}
        if use_interrupt:
            from langgraph.types import interrupt

            decision = interrupt({"action": "review_export", "case_dir": state.get("case_dir")})
            approved = bool(decision.get("export_approved"))
            return {
                "export_approved": approved,
                "review_required": not approved,
                "status": "export_approved" if approved else "waiting_for_human_review",
            }
        return dict(WAITING)

    return node
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_pipeline_gates.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/case_builder/graph/gates.py tests/test_pipeline_gates.py
git commit -m "feat(graph): add packet and export review gate nodes

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Capture, parse, and draft nodes

**Files:**
- Create: `src/case_builder/graph/pipeline_nodes.py`
- Test: `tests/test_pipeline_nodes.py`

**Interfaces:**
- Consumes: `TrcrRunner`, ops functions (see "Existing interfaces"), `nodes.merge_result` semantics, `nodes.required_case_dir`.
- Produces: `merge_results(state: GraphState, results: list[OpResult], success_status: str) -> GraphState` (multi-result fold with the same keys as `merge_result`), plus node factories `source_capture_node(runner)`, `parse_or_ocr_node(runner)`, `draft_packets_node(runner)`. Status vocabulary produced here and relied on downstream: `source_capture_skipped`, `sources_captured`, `parse_skipped_dry_run`, `sources_parsed`, `draft_skipped_no_sources`, `packets_drafted`, `error`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_pipeline_nodes.py`:

```python
from pathlib import Path

from case_builder.graph.pipeline_nodes import (
    draft_packets_node,
    merge_results,
    source_capture_node,
)
from case_builder.ops.result import OpResult
from case_builder.ops.runner import TrcrRunner

REPO_ROOT = Path(__file__).resolve().parents[1]


def dry_runner() -> TrcrRunner:
    return TrcrRunner(repo_root=REPO_ROOT, dry_run=True)


def test_merge_results_folds_commands_and_errors():
    state = {"planned_commands": [["old"]], "tool_results": [], "errors": ["old error"]}
    results = [
        OpResult(name="a", command=["cmd", "a"]),
        OpResult(name="b", ok=False, command=["cmd", "b"], errors=["b failed"]),
    ]

    update = merge_results(state, results, "done")

    assert update["planned_commands"] == [["old"], ["cmd", "a"], ["cmd", "b"]]
    assert [item["name"] for item in update["tool_results"]] == ["a", "b"]
    assert update["errors"] == ["old error", "b failed"]
    assert update["status"] == "error"


def test_merge_results_success_status_when_all_ok():
    update = merge_results({}, [OpResult(name="a", command=["x"])], "done")

    assert update["status"] == "done"


def test_source_capture_skips_without_urls():
    node = source_capture_node(dry_runner())

    update = node({"case_dir": "data/cases/x"})

    assert update["status"] == "source_capture_skipped"


def test_source_capture_plans_ingest_per_url():
    node = source_capture_node(dry_runner())

    update = node({"case_dir": "data/cases/x", "source_urls": ["https://a.example", "https://b.example"]})

    assert update["status"] == "sources_captured"
    assert [item["name"] for item in update["tool_results"]] == ["ingest_url", "ingest_url"]
    assert update["planned_commands"][0][2] == "ingest-url"


def test_draft_packets_skips_in_dry_run_without_source_ids():
    node = draft_packets_node(dry_runner())

    update = node({"case_dir": "data/cases/x"})

    assert update["status"] == "draft_skipped_no_sources"


def test_draft_packets_plans_draft_per_source_id():
    node = draft_packets_node(dry_runner())

    update = node({"case_dir": "data/cases/x", "source_ids": ["S0001", "S0002"]})

    assert update["status"] == "packets_drafted"
    assert len(update["planned_commands"]) == 2
    assert update["planned_commands"][0][2] == "draft-extraction"


def test_parse_or_ocr_skips_in_dry_run():
    from case_builder.graph.pipeline_nodes import parse_or_ocr_node

    node = parse_or_ocr_node(dry_runner())

    update = node({"case_dir": "data/cases/x"})

    assert update["status"] == "parse_skipped_dry_run"


def test_parse_or_ocr_records_runtime_errors_per_source(synthetic_case_copy):
    from case_builder.graph.pipeline_nodes import parse_or_ocr_node

    node = parse_or_ocr_node(TrcrRunner(repo_root=REPO_ROOT, dry_run=False))

    update = node({"case_dir": str(synthetic_case_copy)})

    # Synthetic case sources either already have text or lack local raw files /
    # Docling; the node must finish without raising and report per-source issues.
    assert update["status"] in {"sources_parsed", "error"}
    assert isinstance(update.get("errors", []), list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_pipeline_nodes.py -v`
Expected: FAIL with `ModuleNotFoundError` for `case_builder.graph.pipeline_nodes`

- [ ] **Step 3: Write minimal implementation**

Create `src/case_builder/graph/pipeline_nodes.py`:

```python
"""Deterministic pipeline nodes between planning and export, over the ops core."""

from __future__ import annotations

from ..ops import case as case_ops
from ..ops import exports as export_ops
from ..ops import extraction as extraction_ops
from ..ops import query as query_ops
from ..ops import review as review_ops
from ..ops import sources as source_ops
from ..ops.result import OpResult
from ..ops.runner import TrcrRunner
from .nodes import required_case_dir
from .state import GraphState


def merge_results(state: GraphState, results: list[OpResult], success_status: str) -> GraphState:
    planned = list(state.get("planned_commands") or [])
    tools = list(state.get("tool_results") or [])
    errors = list(state.get("errors") or [])
    ok = True
    for result in results:
        planned.append(result.command)
        tools.append(result.to_dict())
        errors.extend(result.errors)
        ok = ok and result.ok
    return {
        "planned_commands": planned,
        "tool_results": tools,
        "errors": errors,
        "status": success_status if ok else "error",
    }


def source_capture_node(runner: TrcrRunner):
    def node(state: GraphState) -> GraphState:
        urls = state.get("source_urls") or []
        if not urls:
            return {"status": "source_capture_skipped"}
        case_dir = required_case_dir(state)
        results = [source_ops.ingest_url(runner, case_dir, url) for url in urls]
        return merge_results(state, results, "sources_captured")

    return node


def parse_or_ocr_node(runner: TrcrRunner):
    def node(state: GraphState) -> GraphState:
        if runner.dry_run:
            return {"status": "parse_skipped_dry_run"}
        case_dir = required_case_dir(state)
        sources = query_ops.get_records(case_dir, "sources", include_private=True)
        if not sources.ok:
            return merge_results(state, [sources], "error")
        results: list[OpResult] = []
        extra_errors: list[str] = []
        for source in sources.data["records"]:
            if source.get("text_path") or not source.get("raw_path"):
                continue
            source_id = str(source.get("source_id"))
            try:
                if str(source["raw_path"]).lower().endswith(".pdf"):
                    results.append(source_ops.ocr_source(case_dir, source_id))
                else:
                    results.append(source_ops.parse_source(case_dir, source_id))
            except RuntimeError as exc:
                extra_errors.append(f"parse_or_ocr {source_id}: {exc}")
        merged = merge_results(state, results, "sources_parsed")
        merged["errors"] = [*merged["errors"], *extra_errors]
        return merged

    return node


def draft_packets_node(runner: TrcrRunner):
    def node(state: GraphState) -> GraphState:
        case_dir = required_case_dir(state)
        source_ids = list(state.get("source_ids") or [])
        if not source_ids and not runner.dry_run:
            records = query_ops.get_records(case_dir, "sources", include_private=True)
            if records.ok:
                source_ids = [str(row["source_id"]) for row in records.data["records"] if row.get("source_id")]
        if not source_ids:
            return {"status": "draft_skipped_no_sources"}
        results = [extraction_ops.draft_extraction(runner, case_dir, source_id) for source_id in source_ids]
        merged = merge_results(state, results, "packets_drafted")
        if not runner.dry_run:
            listed = extraction_ops.list_packets(case_dir)
            if listed.ok:
                merged["packets"] = list(listed.data["packets"])
        return merged

    return node
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_pipeline_nodes.py -v && .venv/bin/python -m pytest tests/test_case_builder_structure.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/case_builder/graph/pipeline_nodes.py tests/test_pipeline_nodes.py
git commit -m "feat(graph): add capture, parse, and draft pipeline nodes

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Import, index, audit, and export nodes

**Files:**
- Modify: `src/case_builder/graph/pipeline_nodes.py` (append four factories)
- Test: `tests/test_pipeline_nodes.py` (append tests)

**Interfaces:**
- Consumes: Task 3's `merge_results`, ops functions.
- Produces: `import_and_validate_node(runner)`, `index_case_node(runner)`, `readiness_audit_node(runner)`, `export_bundle_node(runner)`. Statuses: `import_skipped_no_approved_packets`, `imported_and_validated`, `index_skipped`, `index_failed`, `case_indexed`, `readiness_audited`, `bundle_exported` (also sets `review_required: False`).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_pipeline_nodes.py`:

```python
def test_import_and_validate_skips_without_approvals():
    from case_builder.graph.pipeline_nodes import import_and_validate_node

    node = import_and_validate_node(dry_runner())

    update = node({"case_dir": "data/cases/x"})

    assert update["status"] == "import_skipped_no_approved_packets"


def test_import_and_validate_imports_each_approved_packet_with_confirm():
    from case_builder.graph.pipeline_nodes import import_and_validate_node

    node = import_and_validate_node(dry_runner())

    update = node({"case_dir": "data/cases/x", "approved_packets": ["S1_extraction.json", "S2_extraction.json"]})

    assert update["status"] == "imported_and_validated"
    names = [item["name"] for item in update["tool_results"]]
    assert names == ["import_extraction", "import_extraction", "validate"]
    assert update["planned_commands"][0][2] == "import-extraction"
    assert update["planned_commands"][0][4].endswith("staging/extractions/S1_extraction.json")
    assert not update["errors"]  # confirm=True flowed through the gate


def test_index_node_skips_unless_enabled():
    from case_builder.graph.pipeline_nodes import index_case_node

    node = index_case_node(dry_runner())

    assert node({"case_dir": "data/cases/x"})["status"] == "index_skipped"
    assert node({"case_dir": "data/cases/x", "index_enabled": True})["status"] == "index_skipped"  # dry run


def test_index_node_reports_failure_without_raising(synthetic_case_copy):
    from case_builder.graph.pipeline_nodes import index_case_node
    from case_builder.ops.runner import TrcrRunner

    node = index_case_node(TrcrRunner(repo_root=REPO_ROOT, dry_run=False))

    update = node({"case_dir": str(synthetic_case_copy), "index_enabled": True})

    # Retrieval extras / Qdrant are not available in CI: the node must degrade.
    assert update["status"] in {"case_indexed", "index_failed"}


def test_readiness_audit_runs_four_audits():
    from case_builder.graph.pipeline_nodes import readiness_audit_node

    node = readiness_audit_node(dry_runner())

    update = node({"case_dir": "data/cases/x"})

    subcommands = [command[2] for command in update["planned_commands"]]
    assert subcommands == [
        "audit-contradictions",
        "review-narrative-readiness",
        "audit-privacy-redactions",
        "audit-source-independence",
    ]
    assert update["status"] == "readiness_audited"


def test_export_bundle_exports_manim_and_report():
    from case_builder.graph.pipeline_nodes import export_bundle_node

    node = export_bundle_node(dry_runner())

    update = node({"case_dir": "data/cases/x"})

    subcommands = [command[2] for command in update["planned_commands"]]
    assert subcommands == ["export-manim", "report"]
    assert update["status"] == "bundle_exported"
    assert update["review_required"] is False
    assert "--include-private" not in update["planned_commands"][0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_pipeline_nodes.py -v`
Expected: new tests FAIL with `ImportError` (factories not defined); Task 3 tests still PASS

- [ ] **Step 3: Write minimal implementation**

Append to `src/case_builder/graph/pipeline_nodes.py`:

```python
def import_and_validate_node(runner: TrcrRunner):
    def node(state: GraphState) -> GraphState:
        approved = state.get("approved_packets") or []
        if not approved:
            return {"status": "import_skipped_no_approved_packets"}
        case_dir = required_case_dir(state)
        results = [
            extraction_ops.import_extraction(
                runner,
                case_dir,
                f"{case_dir.rstrip('/')}/staging/extractions/{name}",
                confirm=True,
            )
            for name in approved
        ]
        results.append(case_ops.validate(runner, case_dir))
        return merge_results(state, results, "imported_and_validated")

    return node


def index_case_node(runner: TrcrRunner):
    def node(state: GraphState) -> GraphState:
        if not state.get("index_enabled") or runner.dry_run:
            return {"status": "index_skipped"}
        case_dir = required_case_dir(state)
        try:
            result = query_ops.index_case(case_dir)
        except Exception as exc:  # optional retrieval deps or Qdrant may be absent
            return {
                "status": "index_failed",
                "errors": [*(state.get("errors") or []), f"index_case: {exc}"],
            }
        return merge_results(state, [result], "case_indexed")

    return node


def readiness_audit_node(runner: TrcrRunner):
    def node(state: GraphState) -> GraphState:
        case_dir = required_case_dir(state)
        results = [
            review_ops.audit_contradictions(runner, case_dir),
            review_ops.review_narrative_readiness(runner, case_dir),
            review_ops.audit_privacy_redactions(runner, case_dir),
            review_ops.audit_source_independence(runner, case_dir),
        ]
        return merge_results(state, results, "readiness_audited")

    return node


def export_bundle_node(runner: TrcrRunner):
    def node(state: GraphState) -> GraphState:
        case_dir = required_case_dir(state)
        results = [export_ops.export_manim(runner, case_dir), case_ops.report(runner, case_dir)]
        merged = merge_results(state, results, "bundle_exported")
        merged["review_required"] = False
        return merged

    return node
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_pipeline_nodes.py tests/test_case_builder_structure.py -v`
Expected: PASS (structure test guards the 200-LOC ceiling — `pipeline_nodes.py` lands around 160 non-comment LOC)

- [ ] **Step 5: Commit**

```bash
git add src/case_builder/graph/pipeline_nodes.py tests/test_pipeline_nodes.py
git commit -m "feat(graph): add import, index, audit, and export pipeline nodes

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Runner wiring — full pipeline, conditional gate edges, checkpointer

**Files:**
- Modify: `src/case_builder/graph/runner.py` (full rewrite shown below)
- Create: `src/case_builder/graph/checkpoint.py`
- Test: `tests/test_pipeline_runner.py`

**Interfaces:**
- Consumes: all node factories from Tasks 2–4, existing bootstrap nodes.
- Produces:
  - `pipeline_nodes_list(runner: TrcrRunner, *, use_interrupt: bool) -> list[tuple[str, Callable]]` — ordered `(name, node)` pairs.
  - `run_sequential(state: CaseBuilderState, runner: TrcrRunner) -> dict` — runs the full pipeline, **stopping when `status == "waiting_for_human_review"`**.
  - `build_case_builder_graph(runner: TrcrRunner, *, checkpointer=None, use_interrupt: bool = False)` — compiled graph with conditional edges routing waiting/rejected gate states to END.
  - `checkpoint.case_checkpointer(case_dir: str)` — returns a `SqliteSaver` on `<case_dir>/.runs/checkpoints.db` (creates the directory); raises `RuntimeError` with an install hint if the sqlite checkpointer is missing.

- [ ] **Step 1: Write the failing test**

Create `tests/test_pipeline_runner.py`:

```python
from pathlib import Path

from case_builder.graph.runner import run_sequential
from case_builder.models.state import CaseBuilderState
from case_builder.ops.runner import TrcrRunner

REPO_ROOT = Path(__file__).resolve().parents[1]


def dry_runner() -> TrcrRunner:
    return TrcrRunner(repo_root=REPO_ROOT, dry_run=True)


def test_sequential_dry_run_stops_at_packet_gate():
    result = run_sequential(
        CaseBuilderState(case_dir="data/cases/example_case", title="Example", subject="missing person map"),
        dry_runner(),
    )

    assert result["status"] == "waiting_for_human_review"
    assert result["review_required"] is True
    # Nothing after the packet gate ran:
    subcommands = [command[2] for command in result["planned_commands"]]
    assert "import-extraction" not in subcommands
    assert "export-manim" not in subcommands


def test_sequential_full_pass_with_preapprovals_runs_whole_pipeline():
    result = run_sequential(
        CaseBuilderState(
            case_dir="data/cases/example_case",
            title="Example",
            subject="missing person map",
            source_urls=["https://example.com/story"],
            source_ids=["S0001"],
            approved_packets=["S0001_extraction.json"],
            export_approved=True,
        ),
        dry_runner(),
    )

    assert result["status"] == "bundle_exported"
    assert result["review_required"] is False
    subcommands = [command[2] for command in result["planned_commands"]]
    assert subcommands == [
        "init-case",
        "plan-public-records",
        "ingest-url",
        "draft-extraction",
        "import-extraction",
        "validate",
        "audit-contradictions",
        "review-narrative-readiness",
        "audit-privacy-redactions",
        "audit-source-independence",
        "export-manim",
        "report",
    ]


def test_checkpointer_creates_runs_db(tmp_path):
    import pytest

    pytest.importorskip("langgraph")
    from case_builder.graph.checkpoint import case_checkpointer

    saver = case_checkpointer(str(tmp_path / "some_case"))

    assert (tmp_path / "some_case" / ".runs" / "checkpoints.db").exists()
    assert saver is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_pipeline_runner.py -v`
Expected: FAIL — `run_sequential` still runs the 4-node bootstrap (first test fails on planned command content; second fails with wrong status; third fails with `ModuleNotFoundError` for `checkpoint`)

- [ ] **Step 3: Write the implementation**

Create `src/case_builder/graph/checkpoint.py`:

```python
"""SQLite checkpointer for durable, resumable case-builder runs."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def case_checkpointer(case_dir: str):
    """Return a SqliteSaver persisted under <case_dir>/.runs/checkpoints.db."""
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError as exc:
        raise RuntimeError(
            "Checkpointing requires langgraph-checkpoint-sqlite. Install with `pip install -e '.[agentic]'`."
        ) from exc
    db_path = Path(case_dir) / ".runs" / "checkpoints.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path), check_same_thread=False)
    return SqliteSaver(connection)
```

Note: `sqlite3.connect` creates the `.db` file lazily on some platforms; if the
`assert ... .exists()` in the test fails, add `connection.execute("PRAGMA user_version;")`
after connecting to force file creation — keep the test as written.

Replace the entire content of `src/case_builder/graph/runner.py` with:

```python
"""Graph construction plus deterministic local execution fallback."""

from __future__ import annotations

from ..models.state import CaseBuilderState
from ..ops.runner import TrcrRunner
from .gates import export_review_gate_node, packet_review_gate_node
from .nodes import infer_lanes_node, init_case_node, plan_public_records_node
from .pipeline_nodes import (
    draft_packets_node,
    export_bundle_node,
    import_and_validate_node,
    index_case_node,
    parse_or_ocr_node,
    readiness_audit_node,
    source_capture_node,
)
from .state import GraphState

GATE_TARGETS = {"packet_review_gate": "import_and_validate", "export_review_gate": "export_bundle"}
STOP_STATUSES = {"waiting_for_human_review", "packets_rejected"}


def pipeline_nodes_list(runner: TrcrRunner, *, use_interrupt: bool):
    return [
        ("infer_lanes", infer_lanes_node),
        ("init_case", init_case_node(runner)),
        ("plan_public_records", plan_public_records_node(runner)),
        ("source_capture", source_capture_node(runner)),
        ("parse_or_ocr", parse_or_ocr_node(runner)),
        ("draft_packets", draft_packets_node(runner)),
        ("packet_review_gate", packet_review_gate_node(use_interrupt)),
        ("import_and_validate", import_and_validate_node(runner)),
        ("index_case", index_case_node(runner)),
        ("readiness_audit", readiness_audit_node(runner)),
        ("export_review_gate", export_review_gate_node(use_interrupt)),
        ("export_bundle", export_bundle_node(runner)),
    ]


def run_sequential(state: CaseBuilderState, runner: TrcrRunner) -> dict[str, object]:
    current: GraphState = state.to_dict()
    for _name, node in pipeline_nodes_list(runner, use_interrupt=False):
        current.update(node(current))
        if current.get("status") in STOP_STATUSES:
            break
    current["runner"] = "sequential"
    return dict(current)


def build_case_builder_graph(runner: TrcrRunner, *, checkpointer=None, use_interrupt: bool = False):
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError("LangGraph is not installed. Install with `pip install -e '.[agentic]'`.") from exc

    nodes = pipeline_nodes_list(runner, use_interrupt=use_interrupt)
    graph = StateGraph(GraphState)
    for name, node in nodes:
        graph.add_node(name, node)
    names = [name for name, _ in nodes]
    graph.add_edge(START, names[0])
    for previous, upcoming in zip(names, names[1:]):
        if previous in GATE_TARGETS:
            continue
        graph.add_edge(previous, upcoming)
    for gate, target in GATE_TARGETS.items():
        graph.add_conditional_edges(gate, _gate_router(target, END))
    graph.add_edge(names[-1], END)
    return graph.compile(checkpointer=checkpointer)


def _gate_router(target: str, end):
    def route(state: GraphState):
        return end if state.get("status") in STOP_STATUSES else target

    return route


def langgraph_available() -> bool:
    try:
        import langgraph  # noqa: F401
    except ImportError:
        return False
    return True
```

- [ ] **Step 4: Run tests to verify pass, including the canary**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_pipeline_runner.py tests/test_case_builder.py -v`
Expected: PASS. The canary (`test_case_builder.py`) still sees `status="waiting_for_human_review"`, `review_required=True`, and `tool_results` names exactly `["init_case", "plan_public_records"]` — capture/parse/draft all skip in a dry run with no URLs or source IDs.

- [ ] **Step 5: Run the full suite**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest -q`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/case_builder/graph/runner.py src/case_builder/graph/checkpoint.py tests/test_pipeline_runner.py
git commit -m "feat(graph): wire full pipeline with gate routing and sqlite checkpointer

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: LangGraph interrupt/resume durability test

**Files:**
- Test: `tests/test_langgraph_resume.py` (test-only task — proves the Task 2+5 code works under the real LangGraph runtime and survives a "restart")

**Interfaces:**
- Consumes: `build_case_builder_graph(runner, checkpointer=..., use_interrupt=True)`, `SqliteSaver`, `langgraph.types.Command`.
- Produces: nothing new — a regression net for the interrupt/resume contract: resume payload keys `approved_packets`, `rejected_packets`, `export_approved`.

- [ ] **Step 1: Write the test (it should pass immediately if Tasks 2+5 are correct)**

Create `tests/test_langgraph_resume.py`:

```python
import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("langgraph")

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from case_builder.graph.runner import build_case_builder_graph
from case_builder.models.state import CaseBuilderState
from case_builder.ops.runner import TrcrRunner

REPO_ROOT = Path(__file__).resolve().parents[1]


def make_graph(db_path: Path):
    """Build a fresh graph + saver on the same DB, simulating a process restart."""
    connection = sqlite3.connect(str(db_path), check_same_thread=False)
    runner = TrcrRunner(repo_root=REPO_ROOT, dry_run=True)
    return build_case_builder_graph(runner, checkpointer=SqliteSaver(connection), use_interrupt=True)


def test_interrupt_resume_survives_graph_rebuild(tmp_path):
    db_path = tmp_path / "checkpoints.db"
    config = {"configurable": {"thread_id": "t-resume-1"}}
    state = CaseBuilderState(case_dir="data/cases/example_case", subject="missing person map")

    # Run 1: pauses at the packet review gate.
    graph = make_graph(db_path)
    graph.invoke(state.to_dict(), config)
    snapshot = graph.get_state(config)
    assert "packet_review_gate" in snapshot.next

    # "Restart": brand-new graph over the same sqlite file, then approve a packet.
    graph = make_graph(db_path)
    graph.invoke(Command(resume={"approved_packets": ["S0001_extraction.json"]}), config)
    snapshot = graph.get_state(config)
    assert "export_review_gate" in snapshot.next
    values = snapshot.values
    subcommands = [command[2] for command in values["planned_commands"]]
    assert "import-extraction" in subcommands
    assert "audit-contradictions" in subcommands

    # Final resume: approve the export; run completes.
    graph = make_graph(db_path)
    result = graph.invoke(Command(resume={"export_approved": True}), config)
    assert result["status"] == "bundle_exported"
    assert result["review_required"] is False
    subcommands = [command[2] for command in result["planned_commands"]]
    assert subcommands[-2:] == ["export-manim", "report"]


def test_rejecting_all_packets_ends_the_run(tmp_path):
    db_path = tmp_path / "checkpoints.db"
    config = {"configurable": {"thread_id": "t-reject-1"}}
    state = CaseBuilderState(case_dir="data/cases/example_case", subject="missing person map")

    graph = make_graph(db_path)
    graph.invoke(state.to_dict(), config)
    result = graph.invoke(
        Command(resume={"approved_packets": [], "rejected_packets": [{"packet": "S1.json", "reason": "bad extraction"}]}),
        config,
    )

    assert result["status"] == "packets_rejected"
    snapshot = graph.get_state(config)
    assert snapshot.next == ()  # routed to END, nothing pending
    subcommands = [command[2] for command in result["planned_commands"]]
    assert "import-extraction" not in subcommands
```

- [ ] **Step 2: Run the test**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_langgraph_resume.py -v`
Expected: PASS. If `snapshot.next` assertions fail, debug the gate/conditional-edge wiring from Task 5 — do not weaken the assertions; the pause points are the contract the resume CLI depends on.

- [ ] **Step 3: Commit**

```bash
git add tests/test_langgraph_resume.py
git commit -m "test(graph): cover interrupt/resume durability across graph rebuilds

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Service checkpoint wiring, resume API, and CLI

**Files:**
- Modify: `src/case_builder/app/service.py` (full rewrite shown below)
- Modify: `src/case_builder/cli.py` (plan flags + resume subcommand)
- Test: `tests/test_service_resume.py`

**Interfaces:**
- Consumes: `build_case_builder_graph`, `run_sequential`, `case_checkpointer`, `CaseBuilderState` (with `thread_id`), `langgraph.types.Command`.
- Produces:
  - `run_case_builder(state, *, execute=False, runner="auto", checkpoint=False) -> dict` — when `checkpoint=True` (langgraph only): builds with `case_checkpointer(state.case_dir)` and `use_interrupt=True`, invokes with `{"configurable": {"thread_id": state.thread_id}}`, and adds `thread_id` and `paused_before: list[str]` to the result. `checkpoint=True` with the sequential runner raises `RuntimeError`.
  - `resume_case_builder(case_dir, *, thread_id, approved_packets=(), rejected_packets=(), export_approved=False, execute=False, ) -> dict` — resumes a checkpointed thread via `Command(resume=payload)`; result carries `thread_id`, `paused_before`, `runner="langgraph"`.
  - CLI: `plan` gains `--source-url` (repeatable), `--source-id` (repeatable), `--index`, `--checkpoint`, `--thread`; new `resume` subcommand with `case_dir`, `--thread` (required), `--approve-packet` (repeatable), `--reject-packet` (repeatable), `--reason`, `--approve-export`, `--execute`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_service_resume.py`:

```python
from pathlib import Path

import pytest

from case_builder.cli import build_parser

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_plan_parser_accepts_pipeline_flags():
    parser = build_parser()

    args = parser.parse_args(
        [
            "plan",
            "data/cases/x",
            "--subject",
            "test",
            "--source-url",
            "https://a.example",
            "--source-id",
            "S0001",
            "--index",
            "--checkpoint",
            "--thread",
            "t1",
        ]
    )

    assert args.source_url == ["https://a.example"]
    assert args.source_id == ["S0001"]
    assert args.index is True
    assert args.checkpoint is True
    assert args.thread == "t1"


def test_resume_parser_accepts_review_decisions():
    parser = build_parser()

    args = parser.parse_args(
        [
            "resume",
            "data/cases/x",
            "--thread",
            "t1",
            "--approve-packet",
            "S1_extraction.json",
            "--reject-packet",
            "S2_extraction.json",
            "--reason",
            "insufficient sourcing",
            "--approve-export",
        ]
    )

    assert args.command == "resume"
    assert args.approve_packet == ["S1_extraction.json"]
    assert args.reject_packet == ["S2_extraction.json"]
    assert args.approve_export is True


def test_checkpoint_requires_langgraph_runner():
    from case_builder.app.service import run_case_builder
    from case_builder.models.state import CaseBuilderState

    with pytest.raises(RuntimeError):
        run_case_builder(CaseBuilderState(case_dir="data/cases/x"), runner="sequential", checkpoint=True)


def test_service_checkpoint_pause_and_resume(tmp_path):
    pytest.importorskip("langgraph")
    from case_builder.app.service import resume_case_builder, run_case_builder
    from case_builder.models.state import CaseBuilderState

    case_dir = str(tmp_path / "svc_case")
    state = CaseBuilderState(case_dir=case_dir, subject="missing person map", thread_id="svc-t1")

    first = run_case_builder(state, execute=False, runner="langgraph", checkpoint=True)
    assert first["thread_id"] == "svc-t1"
    assert first["paused_before"] == ["packet_review_gate"]

    second = resume_case_builder(case_dir, thread_id="svc-t1", approved_packets=["S1_extraction.json"])
    assert second["paused_before"] == ["export_review_gate"]

    final = resume_case_builder(case_dir, thread_id="svc-t1", export_approved=True)
    assert final["paused_before"] == []
    assert final["status"] == "bundle_exported"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_service_resume.py -v`
Expected: FAIL — parser rejects `--source-url` (unrecognized argument), `run_case_builder` rejects `checkpoint` kwarg

- [ ] **Step 3: Rewrite `app/service.py`**

Replace the entire content of `src/case_builder/app/service.py` with:

```python
"""Application service boundary for case-builder workflow runs."""

from __future__ import annotations

from typing import Any, Literal, Sequence

from ..graph.checkpoint import case_checkpointer
from ..graph.runner import build_case_builder_graph, langgraph_available, run_sequential
from ..models.state import CaseBuilderState
from ..ops.runner import TrcrRunner

RunnerName = Literal["auto", "langgraph", "sequential"]
LANGGRAPH_HINT = "LangGraph is not installed. Install with `pip install -e '.[agentic]'`."


def run_case_builder(
    state: CaseBuilderState,
    *,
    execute: bool = False,
    runner: RunnerName = "auto",
    checkpoint: bool = False,
) -> dict[str, Any]:
    """Run a case-builder plan and return serializable state.

    Dry runs produce the exact TRCR commands the app would execute. Executed
    runs still stop at human review gates before canonical import or export.
    """
    trcr = TrcrRunner(dry_run=not execute)
    use_langgraph = runner in {"auto", "langgraph"} and langgraph_available()
    if runner == "langgraph" and not langgraph_available():
        raise RuntimeError(LANGGRAPH_HINT)
    if not use_langgraph:
        if checkpoint:
            raise RuntimeError("Checkpointing requires the langgraph runner.")
        return run_sequential(state, trcr)

    payload = state.to_dict()
    if not checkpoint:
        graph = build_case_builder_graph(trcr)
        result = dict(graph.invoke(payload))
        result["runner"] = "langgraph"
        return result

    graph = build_case_builder_graph(trcr, checkpointer=case_checkpointer(state.case_dir), use_interrupt=True)
    config = {"configurable": {"thread_id": payload["thread_id"]}}
    result = dict(graph.invoke(payload, config))
    return _annotate(result, graph, config, payload["thread_id"])


def resume_case_builder(
    case_dir: str,
    *,
    thread_id: str,
    approved_packets: Sequence[str] = (),
    rejected_packets: Sequence[dict[str, Any]] = (),
    export_approved: bool = False,
    execute: bool = False,
) -> dict[str, Any]:
    """Resume a checkpointed run with human review decisions."""
    if not langgraph_available():
        raise RuntimeError(LANGGRAPH_HINT)
    from langgraph.types import Command

    trcr = TrcrRunner(dry_run=not execute)
    graph = build_case_builder_graph(trcr, checkpointer=case_checkpointer(case_dir), use_interrupt=True)
    config = {"configurable": {"thread_id": thread_id}}
    payload = {
        "approved_packets": list(approved_packets),
        "rejected_packets": [dict(item) for item in rejected_packets],
        "export_approved": export_approved,
    }
    result = dict(graph.invoke(Command(resume=payload), config))
    return _annotate(result, graph, config, thread_id)


def _annotate(result: dict[str, Any], graph: Any, config: dict[str, Any], thread_id: str) -> dict[str, Any]:
    snapshot = graph.get_state(config)
    result["paused_before"] = list(snapshot.next)
    result["thread_id"] = thread_id
    result["runner"] = "langgraph"
    return result
```

- [ ] **Step 4: Update the CLI**

In `src/case_builder/cli.py`:

1. Extend the `plan` subparser (after the existing `plan.add_argument("--runner", ...)` line):

```python
    plan.add_argument("--source-url", action="append", default=[], help="Public URL to capture. Repeatable.")
    plan.add_argument("--source-id", action="append", default=[], help="Existing source ID to draft a packet for. Repeatable.")
    plan.add_argument("--index", action="store_true", help="Build the local evidence index after import (execute mode).")
    plan.add_argument("--checkpoint", action="store_true", help="Persist run state to <case>/.runs/checkpoints.db (langgraph only).")
    plan.add_argument("--thread", default=None, help="Thread ID for checkpointed runs. Defaults to the run ID.")
```

2. Add the `resume` subparser (after the `remember` block, before `return parser`):

```python
    resume = sub.add_parser("resume", help="Resume a checkpointed case-builder run with review decisions.")
    resume.add_argument("case_dir")
    resume.add_argument("--thread", required=True, help="Thread ID printed by the checkpointed plan run.")
    resume.add_argument("--approve-packet", action="append", default=[], help="Staged packet filename to approve. Repeatable.")
    resume.add_argument("--reject-packet", action="append", default=[], help="Staged packet filename to reject. Repeatable.")
    resume.add_argument("--reason", default=None, help="Reason recorded for rejected packets.")
    resume.add_argument("--approve-export", action="store_true", help="Approve the public export gate.")
    resume.add_argument("--execute", action="store_true", help="Run TRCR commands instead of dry-running them.")
    resume.set_defaults(handler=run_resume_command)
```

3. Replace `run_plan_command` and add `run_resume_command`:

```python
def run_plan_command(args: argparse.Namespace) -> dict[str, object]:
    state = CaseBuilderState(
        case_dir=args.case_dir,
        title=args.title,
        subject=args.subject,
        lanes=args.lane,
        source_urls=args.source_url,
        source_ids=args.source_id,
        index_enabled=args.index,
        thread_id=args.thread,
    )
    return run_case_builder(state, execute=args.execute, runner=args.runner, checkpoint=args.checkpoint)


def run_resume_command(args: argparse.Namespace) -> dict[str, object]:
    rejected = [{"packet": name, "reason": args.reason} for name in args.reject_packet]
    return resume_case_builder(
        args.case_dir,
        thread_id=args.thread,
        approved_packets=args.approve_packet,
        rejected_packets=rejected,
        export_approved=args.approve_export,
        execute=args.execute,
    )
```

4. Update the service import line:

```python
from .app.service import resume_case_builder, run_case_builder
```

- [ ] **Step 5: Run tests to verify pass**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_service_resume.py tests/test_local_stack.py tests/test_case_builder.py -v`
Expected: PASS (service resume test exercises checkpoint → pause → two resumes end-to-end in dry-run mode)

- [ ] **Step 6: Commit**

```bash
git add src/case_builder/app/service.py src/case_builder/cli.py tests/test_service_resume.py
git commit -m "feat(app): add checkpointed runs and resume command

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: Docs and final sweep

**Files:**
- Modify: `docs/case-builder-langgraph.md`
- Modify: `src/case_builder/graph/README.md`

- [ ] **Step 1: Update `docs/case-builder-langgraph.md`**

Replace the "Bootstrap Workflow" section body (the code block and following paragraph) with:

```markdown
## Pipeline Workflow

```text
infer_lanes -> init_case -> plan_public_records
  -> source_capture -> parse_or_ocr -> draft_packets
  -> packet_review_gate [interrupt]
  -> import_and_validate -> index_case -> readiness_audit
  -> export_review_gate [interrupt]
  -> export_bundle
```

Gates pause the run. Under LangGraph with `--checkpoint`, gates call
`interrupt()` and the run is resumable; in the sequential runner (and
non-checkpointed graphs) an unapproved gate ends the run with
`status: waiting_for_human_review`. Canonical import always flows through
`import_extraction(confirm=True)` downstream of the packet gate.

Checkpointed run and resume:

```bash
trcr-case-builder plan data/cases/example_case \
  --title "Example Case" --subject "Jane Doe missing person" \
  --source-url "https://example.com/story" \
  --runner langgraph --checkpoint --execute

trcr-case-builder resume data/cases/example_case --thread <thread_id> \
  --approve-packet S0001_extraction.json --execute

trcr-case-builder resume data/cases/example_case --thread <thread_id> \
  --approve-export --execute
```

Checkpoints persist in `data/cases/<case>/.runs/checkpoints.db`.
```

Then replace the "Next Nodes" section with:

```markdown
## Next Nodes (Phase 3)

1. `draft_extraction` LLM agent: fill the CLI-drafted packet from parsed source
   text with schema-valid, `status: unverified` output.
2. `readiness_audit` LLM brief: summarize the deterministic audit outputs into
   a reviewer brief (flags, never decides).
3. `lane_router` suggestions: optional LLM lane suggestions recorded with
   rationale, never silently applied.
```

- [ ] **Step 2: Update `src/case_builder/graph/README.md`**

Add rows (or equivalent prose) for the new modules:

```markdown
| `gates.py` | Packet and export review gates; interrupt-based under LangGraph, terminal otherwise. |
| `pipeline_nodes.py` | Deterministic capture/parse/draft/import/index/audit/export nodes over the ops core. |
| `checkpoint.py` | SQLite checkpointer under `<case>/.runs/checkpoints.db` for resumable runs. |
```

- [ ] **Step 3: Final verification sweep**

```bash
cd tc-c-kit
.venv/bin/python -m compileall -q src
.venv/bin/python -m pytest -q
.venv/bin/python -m case_builder.cli plan data/cases/example_case --title "Example" --subject "missing person map" 2>/dev/null | tail -5
```

Expected: compileall silent; full suite green; the CLI dry run prints JSON ending in `"status": "waiting_for_human_review"`.

Note on the last command: it now takes the langgraph path (installed in Task 1) without a checkpointer — the gate returns the waiting status and conditional edges route to END, matching sequential behavior.

- [ ] **Step 4: Commit**

```bash
git add docs/case-builder-langgraph.md src/case_builder/graph/README.md
git commit -m "docs(graph): document full pipeline, gates, and resume workflow

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Self-Review Notes

- **Spec coverage (Phase 2 bullets):** checkpointer → Task 5 (`checkpoint.py`) + Task 7 (service wiring); interrupt/resume → Tasks 2, 6, 7 (`resume` CLI matches the spec's approve/reject semantics; the spec's illustrative `--approve packet:<ID>` syntax is realized as `--approve-packet <name>`); `source_capture` → Task 3; `parse_or_ocr` → Task 3; `import_and_validate` → Task 4; `index_case` → Task 4; `export_bundle` → Task 4. `draft_packets` (deterministic template drafting) and deterministic `readiness_audit` are included so the gates guard real work; their LLM upgrades are Phase 3 and documented as such in Task 8.
- **Safety invariants:** `confirm=True` appears only in `import_and_validate_node`, which is reachable only through the packet gate (conditional edges route unapproved states to END; sequential runner breaks on waiting). Export bundle uses public-safe defaults (asserted in Task 4's test). Automated records/packet linting remain enforced in ops (Phase 1).
- **Type consistency:** node factories all take `TrcrRunner`; gates take `use_interrupt: bool`; `merge_results(state, results, success_status)` used in Tasks 3–4 matches its Task 3 definition; resume payload keys (`approved_packets`, `rejected_packets`, `export_approved`) are identical in gates (Task 2), the durability test (Task 6), and the service/CLI (Task 7); `pipeline_nodes_list` names in Task 5 match the gate-router targets and the `paused_before` assertions in Tasks 6–7.
- **Behavior preservation:** canary assertions hold because in a bare dry run all new pre-gate nodes skip (`source_capture_skipped` → `parse_skipped_dry_run` → `draft_skipped_no_sources`) leaving `tool_results` untouched, and the packet gate reproduces the old terminal state.
- **LangGraph availability:** installed in Task 1; every langgraph-touching test either lives after that task or guards with `importorskip`, so the suite stays green even on a fresh venv without extras.
