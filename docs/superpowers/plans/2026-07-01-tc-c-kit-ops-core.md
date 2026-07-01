# tc-c-kit Ops Core (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract a typed `case_builder/ops/` operations core (with `OpResult` and `policy.py` safety enforcement), re-point the CLI and LangGraph nodes at it, and turn the safety contract into tests.

**Architecture:** Every case operation becomes a typed function returning `OpResult`. A `TrcrRunner` (moved from `tools/trcr_cli.py`) executes `tcr.py` subprocess commands; local-stack Python functions (acquisition/parsing/retrieval) are wrapped directly. `ops/policy.py` is the single enforcement point for staged-write classification, privacy filtering, automation defaults, and guilt-label linting. Frontends (CLI, graph) never touch `tcr.py` or the ledger directly after this phase.

**Tech Stack:** Python ≥3.10 stdlib (dataclasses, subprocess, pathlib), pytest. No new runtime dependencies.

## Global Constraints

- All paths below are relative to the repo root `<projects-root>/true-crime-research` unless prefixed with `tc-c-kit/`.
- Every Python module stays under **200 non-comment LOC** (enforced by `tc-c-kit/tests/test_case_builder_structure.py`).
- Every package directory under `tc-c-kit/src/case_builder/` must contain a `README.md` (same test).
- Python ≥3.10; **no new required dependencies** (`[project] dependencies = []` stays empty).
- Run tests with: `cd tc-c-kit && .venv/bin/python -m pytest <path> -v` (baseline: 38 passed).
- This phase is behavior-preserving: existing tests must keep passing without modifying their assertions. `tests/test_case_builder.py` and `tests/test_local_stack.py` are the regression canaries.
- Commit after every task with a conventional-commit message ending in the Claude co-author trailer:

  ```
  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```

- The synthetic fixture for tests is `tc-c-kit/data/examples/synthetic_case/` (copy into `tmp_path`; never mutate in place).

## File Structure (end state of this phase)

```
tc-c-kit/src/case_builder/ops/
  __init__.py     # re-exports OpResult, TrcrRunner
  README.md       # package purpose + module map
  result.py       # OpResult dataclass + local_op() wrapper for Python-native ops
  runner.py       # TrcrRunner subprocess executor (moved from tools/trcr_cli.py)
  policy.py       # PolicyError, ensure_staged_write, filter_public,
                  # apply_automation_defaults, lint_guilt_labels
  case.py         # init_case, case_info, validate, report
  sources.py      # plan_public_records, add_source, ingest_url, preserve_source,
                  # discover_sources, parse_source, ocr_source
  extraction.py   # draft_extraction, list_packets, read_packet, save_packet,
                  # import_extraction (confirm gate)
  query.py        # get_records, index_case, query_case, link_names
  review.py       # audit_contradictions, review_narrative_readiness,
                  # audit_privacy_redactions, audit_public_export,
                  # audit_source_independence
  exports.py      # export_manim, export_case_charts, export_analysis_charts,
                  # export_timeline

Modified:
  tc-c-kit/src/case_builder/graph/nodes.py       # ops functions instead of CaseBuilderTools
  tc-c-kit/src/case_builder/graph/runner.py      # TrcrRunner injection
  tc-c-kit/src/case_builder/app/service.py       # constructs TrcrRunner
  tc-c-kit/src/case_builder/cli.py               # local-stack handlers go through ops
  tc-c-kit/src/case_builder/README.md            # module map row: tools/ -> ops/
  tc-c-kit/docs/case-builder-langgraph.md        # source-layout table row

Deleted:
  tc-c-kit/src/case_builder/tools/               # entire package (absorbed by ops/runner.py)

New tests:
  tc-c-kit/tests/conftest.py                     # synthetic_case_copy fixture
  tc-c-kit/tests/test_ops_result.py
  tc-c-kit/tests/test_ops_runner.py
  tc-c-kit/tests/test_ops_policy.py
  tc-c-kit/tests/test_ops_case_sources.py
  tc-c-kit/tests/test_ops_extraction.py
  tc-c-kit/tests/test_ops_query_review_exports.py
```

Deliberately out of scope (later phases): `ops` wrappers for `remember_research_actions` (CLI keeps calling `case_builder.memory` directly), provider egress tagging (needs the Phase 3 LLM layer), checkpointer/interrupts, MCP.

---

### Task 1: `ops` package skeleton + `OpResult`

**Files:**
- Create: `tc-c-kit/src/case_builder/ops/__init__.py`
- Create: `tc-c-kit/src/case_builder/ops/README.md`
- Create: `tc-c-kit/src/case_builder/ops/result.py`
- Create: `tc-c-kit/tests/conftest.py`
- Test: `tc-c-kit/tests/test_ops_result.py`

**Interfaces:**
- Consumes: nothing (foundation task).
- Produces: `OpResult` dataclass — fields `name: str`, `ok: bool = True`, `data: dict`, `errors: list[str]`, `warnings: list[str]`, `command: list[str]`, `dry_run: bool = False`, `skipped: bool = False`, `returncode: int = 0`, `stdout: str = ""`, `stderr: str = ""`; method `to_dict() -> dict`. Helper `local_op(name, func, *args, **kwargs) -> OpResult` that converts `CasefileError` into `ok=False`. Fixture `synthetic_case_copy` (a `Path` to a tmp copy of the synthetic case).

- [ ] **Step 1: Write the failing test**

Create `tc-c-kit/tests/conftest.py`:

```python
import shutil
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def synthetic_case_copy(tmp_path: Path) -> Path:
    case_dir = tmp_path / "synthetic_case"
    shutil.copytree(KIT_ROOT / "data" / "examples" / "synthetic_case", case_dir)
    return case_dir
```

Create `tc-c-kit/tests/test_ops_result.py`:

```python
import pytest

from case_builder.casefile import CasefileError
from case_builder.ops.result import OpResult, local_op


def test_op_result_defaults_and_dict_roundtrip():
    result = OpResult(name="validate")

    assert result.ok is True
    assert result.errors == []
    assert result.warnings == []
    assert result.command == []
    payload = result.to_dict()
    assert payload["name"] == "validate"
    assert payload["dry_run"] is False
    assert payload["skipped"] is False


def test_local_op_wraps_return_value_as_data():
    result = local_op("demo", lambda value: {"answer": value}, 42)

    assert result.ok is True
    assert result.data == {"answer": 42}


def test_local_op_converts_casefile_error_to_failure():
    def boom() -> dict:
        raise CasefileError("not a case")

    result = local_op("demo", boom)

    assert result.ok is False
    assert result.errors == ["not a case"]


def test_local_op_lets_unexpected_errors_propagate():
    def boom() -> dict:
        raise ValueError("bug")

    with pytest.raises(ValueError):
        local_op("demo", boom)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_ops_result.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'case_builder.ops'`

- [ ] **Step 3: Write minimal implementation**

Create `tc-c-kit/src/case_builder/ops/result.py`:

```python
"""Shared operation result type for the ops core."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from ..casefile import CasefileError


@dataclass
class OpResult:
    """Uniform result for every case operation across CLI, graph, and MCP."""

    name: str
    ok: bool = True
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    command: list[str] = field(default_factory=list)
    dry_run: bool = False
    skipped: bool = False
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def local_op(name: str, func: Callable[..., dict[str, Any]], /, *args: Any, **kwargs: Any) -> OpResult:
    """Run a Python-native case operation, mapping CasefileError to a failed result."""
    try:
        data = func(*args, **kwargs)
    except CasefileError as exc:
        return OpResult(name=name, ok=False, errors=[str(exc)])
    return OpResult(name=name, data=data)
```

Create `tc-c-kit/src/case_builder/ops/__init__.py`:

```python
"""Typed operations core shared by the CLI, graph nodes, and future MCP server."""

from __future__ import annotations

from .result import OpResult, local_op

__all__ = ["OpResult", "local_op"]
```

Create `tc-c-kit/src/case_builder/ops/README.md`:

```markdown
# case_builder.ops

Typed operations core. Every case operation is a function returning `OpResult`;
frontends (CLI, LangGraph nodes, future MCP server) call these functions and
never touch `tcr.py`, the JSONL ledger, or local-stack modules directly.

| Module | Responsibility |
| --- | --- |
| `result.py` | `OpResult` dataclass and `local_op` wrapper for Python-native ops. |
| `runner.py` | `TrcrRunner` subprocess executor around the repo-local `tcr.py`. |
| `policy.py` | Safety contract as code: staged-write classification, privacy filtering, automation defaults, guilt-label lint. |
| `case.py` | Case lifecycle: init, info, validate, report. |
| `sources.py` | Source intake: planning, registration, ingestion, preservation, discovery, parsing, OCR. |
| `extraction.py` | Extraction packets: drafting, staging reads/writes, gated canonical import. |
| `query.py` | Ledger reads with privacy filtering, retrieval index/query, name linking. |
| `review.py` | Deterministic audits: contradictions, narrative readiness, privacy, public export, source independence. |
| `exports.py` | Public-safe-by-default export commands. |

The safety contract (`docs/skill-api-spec.md`) is enforced here, once, so the
frontends cannot disagree about what is gated.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_ops_result.py tests/test_case_builder_structure.py -v`
Expected: PASS (structure test confirms the new package has a README and stays under the LOC ceiling)

- [ ] **Step 5: Commit**

```bash
git add tc-c-kit/src/case_builder/ops tc-c-kit/tests/conftest.py tc-c-kit/tests/test_ops_result.py
git commit -m "feat(ops): add OpResult and ops package skeleton

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: `TrcrRunner` subprocess executor

**Files:**
- Create: `tc-c-kit/src/case_builder/ops/runner.py`
- Modify: `tc-c-kit/src/case_builder/ops/__init__.py`
- Test: `tc-c-kit/tests/test_ops_runner.py`

**Interfaces:**
- Consumes: `OpResult` from Task 1.
- Produces: `TrcrRunner` class — constructor `TrcrRunner(*, repo_root: Path | None = None, dry_run: bool = True, python_executable: str | None = None)`; methods `run(name: str, args: Sequence[str]) -> OpResult`, `command(args: Sequence[str]) -> list[str]`, `case_path(case_dir: str) -> Path`; attributes `repo_root`, `dry_run`, `tcr_path`. Module functions `default_repo_root() -> Path`, `default_tcr_path(repo_root: Path) -> Path` (moved verbatim from `tools/trcr_cli.py`). Do NOT delete `tools/` yet — that happens in Task 7 after frontends are re-pointed.

- [ ] **Step 1: Write the failing test**

Create `tc-c-kit/tests/test_ops_runner.py`:

```python
import sys
from pathlib import Path

from case_builder.ops.runner import TrcrRunner

KIT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = KIT_ROOT.parent


def test_dry_run_returns_planned_command_without_executing():
    runner = TrcrRunner(repo_root=REPO_ROOT, dry_run=True)

    result = runner.run("validate", ["validate", "data/cases/nonexistent"])

    assert result.ok is True
    assert result.dry_run is True
    assert result.command[0] == sys.executable
    assert result.command[1].endswith("scripts/tcr.py")
    assert result.command[2:] == ["validate", "data/cases/nonexistent"]


def test_executed_run_validates_synthetic_case(synthetic_case_copy):
    runner = TrcrRunner(repo_root=REPO_ROOT, dry_run=False)

    result = runner.run("validate", ["validate", str(synthetic_case_copy)])

    assert result.ok is True
    assert result.returncode == 0
    assert result.dry_run is False


def test_failed_run_reports_error(tmp_path):
    runner = TrcrRunner(repo_root=REPO_ROOT, dry_run=False)

    result = runner.run("validate", ["validate", str(tmp_path / "not_a_case")])

    assert result.ok is False
    assert result.returncode != 0
    assert result.errors


def test_runner_finds_tcr_script():
    runner = TrcrRunner(repo_root=REPO_ROOT)

    assert runner.tcr_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_ops_runner.py -v`
Expected: FAIL with `ModuleNotFoundError` / `ImportError` for `case_builder.ops.runner`

- [ ] **Step 3: Write minimal implementation**

Create `tc-c-kit/src/case_builder/ops/runner.py` (this is `tools/trcr_cli.py` restructured around `OpResult`; the path-discovery helpers move over unchanged):

```python
"""Subprocess executor for the repo-local TRCR CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence

from .result import OpResult


class TrcrRunner:
    """Low-level executor that turns tcr.py invocations into OpResults."""

    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        dry_run: bool = True,
        python_executable: str | None = None,
    ) -> None:
        self.repo_root = repo_root or default_repo_root()
        self.dry_run = dry_run
        self.python_executable = python_executable or sys.executable
        self.tcr_path = default_tcr_path(self.repo_root)

    def command(self, args: Sequence[str]) -> list[str]:
        return [self.python_executable, str(self.tcr_path), *args]

    def case_path(self, case_dir: str) -> Path:
        path = Path(case_dir)
        return path if path.is_absolute() else self.repo_root / path

    def run(self, name: str, args: Sequence[str]) -> OpResult:
        command = self.command(args)
        if self.dry_run:
            return OpResult(name=name, command=command, dry_run=True)
        completed = subprocess.run(command, cwd=self.repo_root, check=False, capture_output=True, text=True)
        ok = completed.returncode == 0
        stderr = completed.stderr.strip()
        return OpResult(
            name=name,
            ok=ok,
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout.strip(),
            stderr=stderr,
            errors=[] if ok else [stderr or f"{name} failed with code {completed.returncode}"],
        )


def default_repo_root() -> Path:
    package_root = Path(__file__).resolve().parents[3]
    cwd = Path.cwd()
    if (cwd / "case.json").exists() or (cwd / "pyproject.toml").exists() or (cwd / "tc-c-kit").exists():
        return cwd
    return package_root


def default_tcr_path(repo_root: Path) -> Path:
    rel = Path(".agents/skills/truecrime-cult-research/scripts/tcr.py")
    candidates = [repo_root, Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parents[3]]
    for root in candidates:
        path = root / rel
        if path.exists():
            return path
    return repo_root / rel
```

Update `tc-c-kit/src/case_builder/ops/__init__.py`:

```python
"""Typed operations core shared by the CLI, graph nodes, and future MCP server."""

from __future__ import annotations

from .result import OpResult, local_op
from .runner import TrcrRunner

__all__ = ["OpResult", "TrcrRunner", "local_op"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_ops_runner.py -v`
Expected: PASS (4 tests; the executed-run test invokes real `tcr.py validate` on the tmp fixture copy — no network)

- [ ] **Step 5: Commit**

```bash
git add tc-c-kit/src/case_builder/ops tc-c-kit/tests/test_ops_runner.py
git commit -m "feat(ops): add TrcrRunner subprocess executor

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: `policy.py` — the safety contract as code

**Files:**
- Create: `tc-c-kit/src/case_builder/ops/policy.py`
- Test: `tc-c-kit/tests/test_ops_policy.py`

**Interfaces:**
- Consumes: `casefile.ensure_case` (existing).
- Produces:
  - `class PolicyError(RuntimeError)`
  - `ALLOWED_WRITE_DIRS: tuple[str, ...] = ("staging", "exports")`
  - `ensure_staged_write(case_dir: str | Path, target: Path) -> None` — raises `PolicyError` if `target` resolves outside the case workspace or outside `ALLOWED_WRITE_DIRS`.
  - `filter_public(records: Iterable[dict], *, include_private: bool = False) -> list[dict]` — drops records whose `public_export` is exactly `False` unless `include_private`.
  - `apply_automation_defaults(record: dict) -> dict` — returns a copy with `status="unverified"`, `confidence` capped at 0.3 (default 0.2), `public_export=False`.
  - `lint_guilt_labels(packet: Any, path: str = "$") -> list[str]` — recursive scan; a string value under keys `("role", "label", "entity_role", "relationship_type")` containing any of `GUILT_LABELS = ("suspect", "perpetrator", "accomplice", "person of interest", "cult member", "co-conspirator")` requires a non-empty sibling `label_source_ids`; each violation yields one problem string.

- [ ] **Step 1: Write the failing test**

Create `tc-c-kit/tests/test_ops_policy.py`:

```python
import pytest

from case_builder.ops.policy import (
    PolicyError,
    apply_automation_defaults,
    ensure_staged_write,
    filter_public,
    lint_guilt_labels,
)


def test_staged_write_allows_staging_and_exports(synthetic_case_copy):
    ensure_staged_write(synthetic_case_copy, synthetic_case_copy / "staging" / "extractions" / "p.json")
    ensure_staged_write(synthetic_case_copy, synthetic_case_copy / "exports" / "evidence_board.md")


def test_staged_write_rejects_canonical_records(synthetic_case_copy):
    with pytest.raises(PolicyError):
        ensure_staged_write(synthetic_case_copy, synthetic_case_copy / "records" / "claims.jsonl")


def test_staged_write_rejects_escape_from_case(synthetic_case_copy):
    with pytest.raises(PolicyError):
        ensure_staged_write(synthetic_case_copy, synthetic_case_copy / "staging" / ".." / ".." / "elsewhere.json")


def test_filter_public_drops_private_records_by_default():
    records = [
        {"claim_id": "C1", "public_export": False},
        {"claim_id": "C2", "public_export": True},
        {"claim_id": "C3"},
    ]

    public = filter_public(records)
    internal = filter_public(records, include_private=True)

    assert [r["claim_id"] for r in public] == ["C2", "C3"]
    assert len(internal) == 3


def test_automation_defaults_force_unverified_private_low_confidence():
    record = apply_automation_defaults({"claim_id": "C1", "status": "corroborated", "confidence": 0.9, "public_export": True})

    assert record["status"] == "unverified"
    assert record["confidence"] <= 0.3
    assert record["public_export"] is False


def test_automation_defaults_fill_missing_confidence():
    record = apply_automation_defaults({"claim_id": "C1"})

    assert record["confidence"] == 0.2


def test_guilt_label_without_citation_is_flagged():
    packet = {"entities": [{"name": "A Person", "role": "suspect"}]}

    problems = lint_guilt_labels(packet)

    assert len(problems) == 1
    assert "suspect" in problems[0]
    assert "label_source_ids" in problems[0]


def test_guilt_label_with_citation_passes():
    packet = {"entities": [{"name": "A Person", "role": "suspect", "label_source_ids": ["S1"]}]}

    assert lint_guilt_labels(packet) == []


def test_neutral_labels_pass():
    packet = {"entities": [{"name": "A Person", "role": "witness"}, {"name": "B", "role": "former_member"}]}

    assert lint_guilt_labels(packet) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_ops_policy.py -v`
Expected: FAIL with `ModuleNotFoundError` for `case_builder.ops.policy`

- [ ] **Step 3: Write minimal implementation**

Create `tc-c-kit/src/case_builder/ops/policy.py`:

```python
"""Safety contract enforcement shared by every ops function."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..casefile import ensure_case

ALLOWED_WRITE_DIRS: tuple[str, ...] = ("staging", "exports")
GUILT_LABELS: tuple[str, ...] = (
    "suspect",
    "perpetrator",
    "accomplice",
    "person of interest",
    "cult member",
    "co-conspirator",
)
LABEL_KEYS: tuple[str, ...] = ("role", "label", "entity_role", "relationship_type")
MAX_AUTOMATION_CONFIDENCE = 0.3
DEFAULT_AUTOMATION_CONFIDENCE = 0.2


class PolicyError(RuntimeError):
    """Raised when an operation would violate the safety contract."""


def ensure_staged_write(case_dir: str | Path, target: Path) -> None:
    """Allow automated writes only under staging/ and exports/ inside the case."""
    case = ensure_case(case_dir)
    try:
        relative = target.resolve().relative_to(case)
    except ValueError as exc:
        raise PolicyError(f"Write outside the case workspace is not allowed: {target}") from exc
    if not relative.parts or relative.parts[0] not in ALLOWED_WRITE_DIRS:
        raise PolicyError(
            "Automated writes must stay under "
            f"{'/'.join(ALLOWED_WRITE_DIRS)}; canonical records go through import_extraction: {relative.as_posix()}"
        )


def filter_public(records: Iterable[dict[str, Any]], *, include_private: bool = False) -> list[dict[str, Any]]:
    """Drop records explicitly marked public_export=false unless include_private."""
    rows = list(records)
    if include_private:
        return rows
    return [row for row in rows if row.get("public_export") is not False]


def apply_automation_defaults(record: dict[str, Any]) -> dict[str, Any]:
    """Automated records are unverified, low-confidence, and private by default."""
    confidence = record.get("confidence")
    try:
        capped = min(float(confidence), MAX_AUTOMATION_CONFIDENCE) if confidence is not None else DEFAULT_AUTOMATION_CONFIDENCE
    except (TypeError, ValueError):
        capped = DEFAULT_AUTOMATION_CONFIDENCE
    return {**record, "status": "unverified", "confidence": capped, "public_export": False}


def lint_guilt_labels(packet: Any, path: str = "$") -> list[str]:
    """Flag guilt-implying labels that lack a citing source (label_source_ids)."""
    problems: list[str] = []
    if isinstance(packet, dict):
        for key, value in packet.items():
            if (
                key in LABEL_KEYS
                and isinstance(value, str)
                and any(label in value.lower() for label in GUILT_LABELS)
                and not packet.get("label_source_ids")
            ):
                problems.append(
                    f"{path}.{key}={value!r} uses a guilt-implying label without "
                    "label_source_ids citing a source that uses this wording"
                )
            problems.extend(lint_guilt_labels(value, f"{path}.{key}"))
    elif isinstance(packet, list):
        for index, item in enumerate(packet):
            problems.extend(lint_guilt_labels(item, f"{path}[{index}]"))
    return problems
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_ops_policy.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add tc-c-kit/src/case_builder/ops/policy.py tc-c-kit/tests/test_ops_policy.py
git commit -m "feat(ops): enforce safety contract in policy module

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: `ops/case.py` and `ops/sources.py`

**Files:**
- Create: `tc-c-kit/src/case_builder/ops/case.py`
- Create: `tc-c-kit/src/case_builder/ops/sources.py`
- Test: `tc-c-kit/tests/test_ops_case_sources.py`

**Interfaces:**
- Consumes: `TrcrRunner` (Task 2), `OpResult`/`local_op` (Task 1), existing `casefile` helpers, existing local-stack functions `case_builder.acquisition.discover_sources`, `case_builder.parsing.parse_source`, `case_builder.parsing.ocr_source`.
- Produces (all return `OpResult`):
  - `case.init_case(runner, case_dir: str, title: str | None = None)` — skips (`skipped=True`) when `case.json` exists, mirroring current `CaseBuilderTools.init_case`.
  - `case.case_info(case_dir: str)` — no runner; reads `case.json` + per-record-type counts.
  - `case.validate(runner, case_dir: str)`
  - `case.report(runner, case_dir: str)`
  - `sources.plan_public_records(runner, case_dir: str, subject: str, lanes: Sequence[str])`
  - `sources.add_source(runner, case_dir, *, title, url=None, source_type=None, reliability_grade=None, author=None, publisher=None, date_published=None, archive_url=None, notes=None, public_export=True)`
  - `sources.ingest_url(runner, case_dir, url, *, title=None, source_type=None, reliability_grade=None, timeout=None, public_export=True)`
  - `sources.preserve_source(runner, case_dir, source_id, *, archive_url=None, content_type=None, out=None)`
  - `sources.discover_sources(case_dir, *, query, searxng_url="http://localhost:8080", limit=10, out=None)`
  - `sources.parse_source(case_dir, source_id, *, force=False)`
  - `sources.ocr_source(case_dir, source_id, *, language="eng", force=False)`

- [ ] **Step 1: Write the failing test**

Create `tc-c-kit/tests/test_ops_case_sources.py`:

```python
from pathlib import Path

from case_builder.ops import case as case_ops
from case_builder.ops import sources as source_ops
from case_builder.ops.runner import TrcrRunner

REPO_ROOT = Path(__file__).resolve().parents[2]


def dry_runner() -> TrcrRunner:
    return TrcrRunner(repo_root=REPO_ROOT, dry_run=True)


def test_init_case_skips_existing_case(synthetic_case_copy):
    result = case_ops.init_case(dry_runner(), str(synthetic_case_copy), "Synthetic Case")

    assert result.skipped is True
    assert result.name == "init_case"


def test_init_case_plans_command_for_new_case(tmp_path):
    result = case_ops.init_case(dry_runner(), str(tmp_path / "new_case"), None)

    assert result.skipped is False
    assert result.dry_run is True
    assert "init-case" in result.command
    assert "--title" in result.command


def test_case_info_counts_records(synthetic_case_copy):
    result = case_ops.case_info(str(synthetic_case_copy))

    assert result.ok is True
    assert result.data["case_id"] == "synthetic_case"
    assert result.data["record_counts"]["sources"] >= 1
    assert result.data["record_counts"]["claims"] >= 1


def test_case_info_fails_on_non_case(tmp_path):
    result = case_ops.case_info(str(tmp_path))

    assert result.ok is False
    assert result.errors


def test_validate_and_report_plan_commands(synthetic_case_copy):
    runner = dry_runner()

    validate = case_ops.validate(runner, str(synthetic_case_copy))
    report = case_ops.report(runner, str(synthetic_case_copy))

    assert validate.command[2] == "validate"
    assert report.command[2] == "report"


def test_plan_public_records_repeats_lane_flags():
    result = source_ops.plan_public_records(dry_runner(), "data/cases/x", "Jane Doe", ["legal-court", "missing-persons"])

    assert result.command[2] == "plan-public-records"
    assert result.command.count("--lane") == 2
    assert "legal-court" in result.command
    assert "missing-persons" in result.command


def test_add_source_builds_optional_flags():
    result = source_ops.add_source(
        dry_runner(),
        "data/cases/x",
        title="A Story",
        url="https://example.com/story",
        source_type="news_article",
        reliability_grade="B",
        public_export=False,
    )

    command = result.command
    assert command[2] == "add-source"
    assert command[command.index("--title") + 1] == "A Story"
    assert command[command.index("--url") + 1] == "https://example.com/story"
    assert command[command.index("--reliability-grade") + 1] == "B"
    assert "--no-public-export" in command


def test_ingest_url_places_url_positionally():
    result = source_ops.ingest_url(dry_runner(), "data/cases/x", "https://example.com/story", source_type="news_article")

    assert result.command[2:5] == ["ingest-url", "data/cases/x", "https://example.com/story"]
    assert "--source-type" in result.command


def test_preserve_source_plans_command():
    result = source_ops.preserve_source(dry_runner(), "data/cases/x", "S0001", archive_url="https://archive.org/x")

    assert result.command[2:5] == ["preserve-source", "data/cases/x", "S0001"]
    assert "--archive-url" in result.command


def test_parse_source_wraps_casefile_error(tmp_path):
    result = source_ops.parse_source(str(tmp_path / "not_a_case"), "S0001")

    assert result.ok is False
    assert result.errors
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_ops_case_sources.py -v`
Expected: FAIL with `ImportError` (modules don't exist)

- [ ] **Step 3: Write minimal implementation**

Create `tc-c-kit/src/case_builder/ops/case.py`:

```python
"""Case lifecycle operations."""

from __future__ import annotations

import json
from typing import Any

from ..casefile import RECORD_FILES, ensure_case, load_records
from .result import OpResult, local_op
from .runner import TrcrRunner


def init_case(runner: TrcrRunner, case_dir: str, title: str | None = None) -> OpResult:
    case_path = runner.case_path(case_dir)
    args = ["init-case", case_dir, "--title", title or case_path.name.replace("_", " ").title()]
    if (case_path / "case.json").exists():
        return OpResult(name="init_case", command=runner.command(args), dry_run=runner.dry_run, skipped=True)
    return runner.run("init_case", args)


def case_info(case_dir: str) -> OpResult:
    return local_op("case_info", _case_info_data, case_dir)


def validate(runner: TrcrRunner, case_dir: str) -> OpResult:
    return runner.run("validate", ["validate", case_dir])


def report(runner: TrcrRunner, case_dir: str) -> OpResult:
    return runner.run("report", ["report", case_dir])


def _case_info_data(case_dir: str) -> dict[str, Any]:
    case = ensure_case(case_dir)
    meta = json.loads((case / "case.json").read_text(encoding="utf-8"))
    counts = {name: len(load_records(case, name)) for name in RECORD_FILES}
    return {"case_id": str(meta.get("case_id") or case.name), "case_json": meta, "record_counts": counts}
```

Create `tc-c-kit/src/case_builder/ops/sources.py`:

```python
"""Source intake operations: planning, registration, discovery, parsing, OCR."""

from __future__ import annotations

from typing import Sequence

from ..acquisition import discover_sources as _discover_sources
from ..parsing import ocr_source as _ocr_source
from ..parsing import parse_source as _parse_source
from .result import OpResult, local_op
from .runner import TrcrRunner


def plan_public_records(runner: TrcrRunner, case_dir: str, subject: str, lanes: Sequence[str]) -> OpResult:
    args = ["plan-public-records", case_dir, "--subject", subject]
    for lane in lanes:
        args.extend(["--lane", lane])
    return runner.run("plan_public_records", args)


def add_source(
    runner: TrcrRunner,
    case_dir: str,
    *,
    title: str,
    url: str | None = None,
    source_type: str | None = None,
    reliability_grade: str | None = None,
    author: str | None = None,
    publisher: str | None = None,
    date_published: str | None = None,
    archive_url: str | None = None,
    notes: str | None = None,
    public_export: bool = True,
) -> OpResult:
    args = ["add-source", case_dir, "--title", title]
    args += _optional_flags(
        ("--url", url),
        ("--source-type", source_type),
        ("--reliability-grade", reliability_grade),
        ("--author", author),
        ("--publisher", publisher),
        ("--date-published", date_published),
        ("--archive-url", archive_url),
        ("--notes", notes),
    )
    if not public_export:
        args.append("--no-public-export")
    return runner.run("add_source", args)


def ingest_url(
    runner: TrcrRunner,
    case_dir: str,
    url: str,
    *,
    title: str | None = None,
    source_type: str | None = None,
    reliability_grade: str | None = None,
    timeout: int | None = None,
    public_export: bool = True,
) -> OpResult:
    args = ["ingest-url", case_dir, url]
    args += _optional_flags(
        ("--title", title),
        ("--source-type", source_type),
        ("--reliability-grade", reliability_grade),
        ("--timeout", str(timeout) if timeout is not None else None),
    )
    if not public_export:
        args.append("--no-public-export")
    return runner.run("ingest_url", args)


def preserve_source(
    runner: TrcrRunner,
    case_dir: str,
    source_id: str,
    *,
    archive_url: str | None = None,
    content_type: str | None = None,
    out: str | None = None,
) -> OpResult:
    args = ["preserve-source", case_dir, source_id]
    args += _optional_flags(("--archive-url", archive_url), ("--content-type", content_type), ("--out", out))
    return runner.run("preserve_source", args)


def discover_sources(
    case_dir: str,
    *,
    query: str,
    searxng_url: str = "http://localhost:8080",
    limit: int = 10,
    out: str | None = None,
) -> OpResult:
    return local_op("discover_sources", _discover_sources, case_dir, query=query, searxng_url=searxng_url, limit=limit, out=out)


def parse_source(case_dir: str, source_id: str, *, force: bool = False) -> OpResult:
    return local_op("parse_source", _parse_source, case_dir, source_id, force=force)


def ocr_source(case_dir: str, source_id: str, *, language: str = "eng", force: bool = False) -> OpResult:
    return local_op("ocr_source", _ocr_source, case_dir, source_id, language=language, force=force)


def _optional_flags(*pairs: tuple[str, str | None]) -> list[str]:
    args: list[str] = []
    for flag, value in pairs:
        if value:
            args.extend([flag, value])
    return args
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_ops_case_sources.py tests/test_case_builder_structure.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tc-c-kit/src/case_builder/ops tc-c-kit/tests/test_ops_case_sources.py
git commit -m "feat(ops): add case lifecycle and source intake operations

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: `ops/extraction.py` — packets and the gated import

**Files:**
- Create: `tc-c-kit/src/case_builder/ops/extraction.py`
- Test: `tc-c-kit/tests/test_ops_extraction.py`

**Interfaces:**
- Consumes: `TrcrRunner`, `OpResult`, `policy.ensure_staged_write`, `policy.lint_guilt_labels`, `policy.PolicyError`, `casefile.ensure_case`, `casefile.log_action`.
- Produces (all return `OpResult`):
  - `draft_extraction(runner, case_dir, source_id, *, template: str = "generic")` — passes `--template` to `tcr.py draft-extraction`.
  - `list_packets(case_dir)` — `data={"packets": [<filenames sorted>]}` from `staging/extractions/`.
  - `read_packet(case_dir, packet_name)` — `data={"packet": <parsed json>, "path": <str>}`; `ok=False` when missing.
  - `save_packet(case_dir, packet_name, packet: dict)` — staged-write check + guilt-label lint; writes pretty JSON; logs `save_extraction_packet` to `research_actions.jsonl`.
  - `import_extraction(runner, case_dir, packet_path: str, *, confirm: bool = False)` — **refuses with `ok=False` and an explanatory error when `confirm` is not `True`; no subprocess runs.** This is the safety invariant: no canonical import without human review.

- [ ] **Step 1: Write the failing test**

Create `tc-c-kit/tests/test_ops_extraction.py`:

```python
import json
from pathlib import Path

from case_builder.ops import extraction as extraction_ops
from case_builder.ops.runner import TrcrRunner

REPO_ROOT = Path(__file__).resolve().parents[2]


def dry_runner() -> TrcrRunner:
    return TrcrRunner(repo_root=REPO_ROOT, dry_run=True)


def test_import_extraction_refuses_without_confirm():
    result = extraction_ops.import_extraction(dry_runner(), "data/cases/x", "staging/extractions/p.json")

    assert result.ok is False
    assert result.command == []
    assert any("confirm" in error for error in result.errors)


def test_import_extraction_plans_command_with_confirm():
    result = extraction_ops.import_extraction(dry_runner(), "data/cases/x", "staging/extractions/p.json", confirm=True)

    assert result.ok is True
    assert result.command[2] == "import-extraction"


def test_draft_extraction_passes_template():
    result = extraction_ops.draft_extraction(dry_runner(), "data/cases/x", "S0001", template="missing-persons")

    assert result.command[2] == "draft-extraction"
    assert result.command[result.command.index("--template") + 1] == "missing-persons"


def test_save_and_read_and_list_packets(synthetic_case_copy):
    packet = {"source_id": "SDEMO0001", "entities": [{"name": "A Witness", "role": "witness"}]}

    saved = extraction_ops.save_packet(str(synthetic_case_copy), "SDEMO0001_extraction.json", packet)
    listed = extraction_ops.list_packets(str(synthetic_case_copy))
    read = extraction_ops.read_packet(str(synthetic_case_copy), "SDEMO0001_extraction.json")

    assert saved.ok is True
    assert "SDEMO0001_extraction.json" in listed.data["packets"]
    assert read.data["packet"] == packet
    actions = (synthetic_case_copy / "records" / "research_actions.jsonl").read_text(encoding="utf-8")
    assert "save_extraction_packet" in actions


def test_save_packet_rejects_guilt_label_without_citation(synthetic_case_copy):
    packet = {"entities": [{"name": "A Person", "role": "suspect"}]}

    result = extraction_ops.save_packet(str(synthetic_case_copy), "bad_packet.json", packet)

    assert result.ok is False
    assert not (synthetic_case_copy / "staging" / "extractions" / "bad_packet.json").exists()


def test_save_packet_rejects_path_escape(synthetic_case_copy):
    result = extraction_ops.save_packet(str(synthetic_case_copy), "../../records/claims.jsonl", {"a": 1})

    assert result.ok is False
    assert (synthetic_case_copy / "records" / "claims.jsonl").read_text(encoding="utf-8")  # untouched, still valid


def test_read_packet_missing_is_failure(synthetic_case_copy):
    result = extraction_ops.read_packet(str(synthetic_case_copy), "nope.json")

    assert result.ok is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_ops_extraction.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

Create `tc-c-kit/src/case_builder/ops/extraction.py`:

```python
"""Extraction packet operations with a gated canonical import."""

from __future__ import annotations

import json
from typing import Any

from ..casefile import ensure_case, log_action
from .policy import PolicyError, ensure_staged_write, lint_guilt_labels
from .result import OpResult, local_op
from .runner import TrcrRunner

IMPORT_REFUSAL = (
    "import_extraction writes canonical records and requires confirm=True "
    "after a human has reviewed the extraction packet."
)


def draft_extraction(runner: TrcrRunner, case_dir: str, source_id: str, *, template: str = "generic") -> OpResult:
    return runner.run("draft_extraction", ["draft-extraction", case_dir, source_id, "--template", template])


def import_extraction(runner: TrcrRunner, case_dir: str, packet_path: str, *, confirm: bool = False) -> OpResult:
    if confirm is not True:
        return OpResult(name="import_extraction", ok=False, errors=[IMPORT_REFUSAL])
    return runner.run("import_extraction", ["import-extraction", case_dir, packet_path])


def list_packets(case_dir: str) -> OpResult:
    def _list(case_dir: str) -> dict[str, Any]:
        staging = ensure_case(case_dir) / "staging" / "extractions"
        names = sorted(path.name for path in staging.glob("*.json")) if staging.exists() else []
        return {"packets": names}

    return local_op("list_packets", _list, case_dir)


def read_packet(case_dir: str, packet_name: str) -> OpResult:
    def _read(case_dir: str, packet_name: str) -> dict[str, Any]:
        path = ensure_case(case_dir) / "staging" / "extractions" / packet_name
        if not path.exists():
            return {}
        return {"packet": json.loads(path.read_text(encoding="utf-8")), "path": str(path)}

    result = local_op("read_packet", _read, case_dir, packet_name)
    if result.ok and not result.data:
        return OpResult(name="read_packet", ok=False, errors=[f"Packet not found: {packet_name}"])
    return result


def save_packet(case_dir: str, packet_name: str, packet: dict[str, Any]) -> OpResult:
    case = ensure_case(case_dir)
    target = case / "staging" / "extractions" / packet_name
    try:
        ensure_staged_write(case, target)
    except PolicyError as exc:
        return OpResult(name="save_packet", ok=False, errors=[str(exc)])
    problems = lint_guilt_labels(packet)
    if problems:
        return OpResult(name="save_packet", ok=False, errors=problems)
    target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log_action(case, "save_extraction_packet", {"packet": target.name})
    return OpResult(name="save_packet", data={"path": str(target)})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_ops_extraction.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add tc-c-kit/src/case_builder/ops/extraction.py tc-c-kit/tests/test_ops_extraction.py
git commit -m "feat(ops): add extraction packet ops with gated canonical import

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: `ops/query.py`, `ops/review.py`, `ops/exports.py`

**Files:**
- Create: `tc-c-kit/src/case_builder/ops/query.py`
- Create: `tc-c-kit/src/case_builder/ops/review.py`
- Create: `tc-c-kit/src/case_builder/ops/exports.py`
- Test: `tc-c-kit/tests/test_ops_query_review_exports.py`

**Interfaces:**
- Consumes: `TrcrRunner`, `OpResult`/`local_op`, `policy.filter_public`, `casefile.load_records`/`RECORD_FILES`, existing `case_builder.retrieval.index_case` / `case_builder.retrieval.query_case`.
- Produces (all return `OpResult`):
  - `query.get_records(case_dir, record_type, *, include_private=False)` — `data={"record_type", "count", "records", "filtered"}`; unknown type → `ok=False` listing valid types.
  - `query.index_case(case_dir, *, include_private=False, qdrant_url="http://localhost:6333", collection=None, embed_model="BAAI/bge-small-en-v1.5")`
  - `query.query_case(case_dir, query_text, *, include_private=False, qdrant_url="http://localhost:6333", collection=None, embed_model="BAAI/bge-small-en-v1.5", top_k=8)`
  - `query.link_names(runner, case_dir, *, names=(), names_file=None)` — repeats `--name` per entry.
  - `review.audit_contradictions(runner, case_dir)`, `review.review_narrative_readiness(runner, case_dir)`, `review.audit_privacy_redactions(runner, case_dir)`, `review.audit_public_export(runner, case_dir)`, `review.audit_source_independence(runner, case_dir)` — plain passthroughs.
  - `exports.export_manim(runner, case_dir, *, include_private=False)`, `exports.export_case_charts(runner, case_dir, *, include_private=False, out_dir=None)`, `exports.export_analysis_charts(runner, case_dir, *, include_private=False, out_dir=None)`, `exports.export_timeline(runner, cases_root, *, include_private=False, out_dir=None)` — `--include-private` appended **only** when explicitly requested (public-safe default).

- [ ] **Step 1: Write the failing test**

Create `tc-c-kit/tests/test_ops_query_review_exports.py`:

```python
import json
from pathlib import Path

from case_builder.ops import exports as export_ops
from case_builder.ops import query as query_ops
from case_builder.ops import review as review_ops
from case_builder.ops.runner import TrcrRunner

REPO_ROOT = Path(__file__).resolve().parents[2]


def dry_runner() -> TrcrRunner:
    return TrcrRunner(repo_root=REPO_ROOT, dry_run=True)


def add_private_claim(case_dir: Path) -> None:
    claims = case_dir / "records" / "claims.jsonl"
    row = {"claim_id": "CPRIVATE", "claim": "Private claim.", "status": "unverified", "confidence": 0.1, "source_ids": ["SDEMO0001"], "public_export": False}
    claims.write_text(claims.read_text(encoding="utf-8") + json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")


def test_get_records_excludes_private_by_default(synthetic_case_copy):
    add_private_claim(synthetic_case_copy)

    public = query_ops.get_records(str(synthetic_case_copy), "claims")
    internal = query_ops.get_records(str(synthetic_case_copy), "claims", include_private=True)

    assert all(row.get("claim_id") != "CPRIVATE" for row in public.data["records"])
    assert public.data["filtered"] == 1
    assert any(row.get("claim_id") == "CPRIVATE" for row in internal.data["records"])


def test_get_records_rejects_unknown_type(synthetic_case_copy):
    result = query_ops.get_records(str(synthetic_case_copy), "nonsense")

    assert result.ok is False
    assert "sources" in result.errors[0]


def test_link_names_repeats_name_flags():
    result = query_ops.link_names(dry_runner(), "data/cases/x", names=["Jane Doe|JD", "John Roe"])

    assert result.command[2] == "link-names"
    assert result.command.count("--name") == 2


def test_review_audits_plan_expected_subcommands():
    runner = dry_runner()
    expectations = {
        review_ops.audit_contradictions: "audit-contradictions",
        review_ops.review_narrative_readiness: "review-narrative-readiness",
        review_ops.audit_privacy_redactions: "audit-privacy-redactions",
        review_ops.audit_public_export: "audit-public-export",
        review_ops.audit_source_independence: "audit-source-independence",
    }

    for func, subcommand in expectations.items():
        assert func(runner, "data/cases/x").command[2] == subcommand


def test_exports_default_public_safe():
    runner = dry_runner()

    public = export_ops.export_manim(runner, "data/cases/x")
    internal = export_ops.export_manim(runner, "data/cases/x", include_private=True)

    assert "--include-private" not in public.command
    assert "--include-private" in internal.command


def test_export_timeline_accepts_out_dir():
    result = export_ops.export_timeline(dry_runner(), "data/cases", out_dir="data/exports/timeline_internal", include_private=True)

    assert result.command[2] == "export-timeline"
    assert result.command[result.command.index("--out-dir") + 1] == "data/exports/timeline_internal"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_ops_query_review_exports.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

Create `tc-c-kit/src/case_builder/ops/query.py`:

```python
"""Ledger reads with privacy filtering, retrieval, and name linking."""

from __future__ import annotations

from typing import Sequence

from ..casefile import RECORD_FILES, CasefileError, load_records
from ..retrieval import index_case as _index_case
from ..retrieval import query_case as _query_case
from .policy import filter_public
from .result import OpResult, local_op
from .runner import TrcrRunner


def get_records(case_dir: str, record_type: str, *, include_private: bool = False) -> OpResult:
    if record_type not in RECORD_FILES:
        return OpResult(
            name="get_records",
            ok=False,
            errors=[f"Unknown record type: {record_type}. Known types: {', '.join(sorted(RECORD_FILES))}"],
        )
    try:
        rows = load_records(case_dir, record_type)
    except CasefileError as exc:
        return OpResult(name="get_records", ok=False, errors=[str(exc)])
    visible = filter_public(rows, include_private=include_private)
    return OpResult(
        name="get_records",
        data={"record_type": record_type, "count": len(visible), "records": visible, "filtered": len(rows) - len(visible)},
    )


def index_case(
    case_dir: str,
    *,
    include_private: bool = False,
    qdrant_url: str = "http://localhost:6333",
    collection: str | None = None,
    embed_model: str = "BAAI/bge-small-en-v1.5",
) -> OpResult:
    return local_op(
        "index_case", _index_case, case_dir,
        include_private=include_private, qdrant_url=qdrant_url, collection=collection, embed_model=embed_model,
    )


def query_case(
    case_dir: str,
    query_text: str,
    *,
    include_private: bool = False,
    qdrant_url: str = "http://localhost:6333",
    collection: str | None = None,
    embed_model: str = "BAAI/bge-small-en-v1.5",
    top_k: int = 8,
) -> OpResult:
    return local_op(
        "query_case", _query_case, case_dir, query_text,
        include_private=include_private, qdrant_url=qdrant_url, collection=collection,
        embed_model=embed_model, top_k=top_k,
    )


def link_names(runner: TrcrRunner, case_dir: str, *, names: Sequence[str] = (), names_file: str | None = None) -> OpResult:
    args = ["link-names", case_dir]
    for name in names:
        args.extend(["--name", name])
    if names_file:
        args.extend(["--names-file", names_file])
    return runner.run("link_names", args)
```

Create `tc-c-kit/src/case_builder/ops/review.py`:

```python
"""Deterministic review audits over the case ledger."""

from __future__ import annotations

from .result import OpResult
from .runner import TrcrRunner


def audit_contradictions(runner: TrcrRunner, case_dir: str) -> OpResult:
    return runner.run("audit_contradictions", ["audit-contradictions", case_dir])


def review_narrative_readiness(runner: TrcrRunner, case_dir: str) -> OpResult:
    return runner.run("review_narrative_readiness", ["review-narrative-readiness", case_dir])


def audit_privacy_redactions(runner: TrcrRunner, case_dir: str) -> OpResult:
    return runner.run("audit_privacy_redactions", ["audit-privacy-redactions", case_dir])


def audit_public_export(runner: TrcrRunner, case_dir: str) -> OpResult:
    return runner.run("audit_public_export", ["audit-public-export", case_dir])


def audit_source_independence(runner: TrcrRunner, case_dir: str) -> OpResult:
    return runner.run("audit_source_independence", ["audit-source-independence", case_dir])
```

Create `tc-c-kit/src/case_builder/ops/exports.py`:

```python
"""Public-safe-by-default export commands."""

from __future__ import annotations

from .result import OpResult
from .runner import TrcrRunner


def export_manim(runner: TrcrRunner, case_dir: str, *, include_private: bool = False) -> OpResult:
    return runner.run("export_manim", _args("export-manim", case_dir, include_private))


def export_case_charts(runner: TrcrRunner, case_dir: str, *, include_private: bool = False, out_dir: str | None = None) -> OpResult:
    return runner.run("export_case_charts", _args("export-case-charts", case_dir, include_private, out_dir))


def export_analysis_charts(runner: TrcrRunner, case_dir: str, *, include_private: bool = False, out_dir: str | None = None) -> OpResult:
    return runner.run("export_analysis_charts", _args("export-analysis-charts", case_dir, include_private, out_dir))


def export_timeline(runner: TrcrRunner, cases_root: str, *, include_private: bool = False, out_dir: str | None = None) -> OpResult:
    return runner.run("export_timeline", _args("export-timeline", cases_root, include_private, out_dir))


def _args(subcommand: str, target: str, include_private: bool, out_dir: str | None = None) -> list[str]:
    args = [subcommand, target]
    if out_dir:
        args.extend(["--out-dir", out_dir])
    if include_private:
        args.append("--include-private")
    return args
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_ops_query_review_exports.py tests/test_case_builder_structure.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tc-c-kit/src/case_builder/ops tc-c-kit/tests/test_ops_query_review_exports.py
git commit -m "feat(ops): add query, review-audit, and export operations

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Re-point graph nodes and app service; delete `tools/`

**Files:**
- Modify: `tc-c-kit/src/case_builder/graph/nodes.py`
- Modify: `tc-c-kit/src/case_builder/graph/runner.py`
- Modify: `tc-c-kit/src/case_builder/app/service.py`
- Delete: `tc-c-kit/src/case_builder/tools/` (entire directory: `__init__.py`, `trcr_cli.py`, `README.md`)
- Test: existing `tc-c-kit/tests/test_case_builder.py` (unchanged — regression canary)

**Interfaces:**
- Consumes: `TrcrRunner` (Task 2), `case_ops.init_case` (Task 4), `source_ops.plan_public_records` (Task 4), `OpResult`.
- Produces: `init_case_node(runner: TrcrRunner)`, `plan_public_records_node(runner: TrcrRunner)`, `run_sequential(state: CaseBuilderState, runner: TrcrRunner)`, `build_case_builder_graph(runner: TrcrRunner)`. `merge_result(state, result: OpResult, success_status)` keys `tool_results` entries by `OpResult.to_dict()` (superset of the old `TrcrToolResult` dict — `name`, `command`, `dry_run`, `returncode`, `stdout`, `stderr`, `skipped` all preserved).

- [ ] **Step 1: Run the canary test to confirm current green**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_case_builder.py -v`
Expected: PASS (this is the behavior we must preserve)

- [ ] **Step 2: Rewrite `graph/nodes.py`**

Replace the entire content of `tc-c-kit/src/case_builder/graph/nodes.py` with:

```python
"""Small graph nodes that adapt agent policy to the ops core."""

from __future__ import annotations

from ..agents.source_lanes import infer_source_lanes
from ..ops import case as case_ops
from ..ops import sources as source_ops
from ..ops.result import OpResult
from ..ops.runner import TrcrRunner
from .state import GraphState


def infer_lanes_node(state: GraphState) -> GraphState:
    lanes = infer_source_lanes(state.get("subject"), state.get("lanes") or [])
    return {"lanes": lanes, "status": "lanes_inferred"}


def init_case_node(runner: TrcrRunner):
    def node(state: GraphState) -> GraphState:
        result = case_ops.init_case(runner, required_case_dir(state), state.get("title"))
        return merge_result(state, result, "case_initialized")

    return node


def plan_public_records_node(runner: TrcrRunner):
    def node(state: GraphState) -> GraphState:
        subject = state.get("subject")
        if not subject:
            return {
                "status": "source_plan_skipped",
                "errors": append_error(state, "No subject provided for source planning."),
            }
        result = source_ops.plan_public_records(runner, required_case_dir(state), subject, state.get("lanes") or [])
        return merge_result(state, result, "source_plan_ready")

    return node


def review_gate_node(state: GraphState) -> GraphState:
    return {
        "review_required": True,
        "status": "waiting_for_human_review",
    }


def merge_result(state: GraphState, result: OpResult, success_status: str) -> GraphState:
    return {
        "planned_commands": [*(state.get("planned_commands") or []), result.command],
        "tool_results": [*(state.get("tool_results") or []), result.to_dict()],
        "errors": [*(state.get("errors") or []), *result.errors],
        "status": success_status if result.ok else "error",
    }


def append_error(state: GraphState, message: str) -> list[str]:
    return [*(state.get("errors") or []), message]


def required_case_dir(state: GraphState) -> str:
    case_dir = state.get("case_dir")
    if not case_dir:
        raise ValueError("case_dir is required")
    return case_dir
```

- [ ] **Step 3: Rewrite `graph/runner.py`**

Replace the entire content of `tc-c-kit/src/case_builder/graph/runner.py` with:

```python
"""Graph construction plus deterministic local execution fallback."""

from __future__ import annotations

from ..models.state import CaseBuilderState
from ..ops.runner import TrcrRunner
from .nodes import infer_lanes_node, init_case_node, plan_public_records_node, review_gate_node
from .state import GraphState


def run_sequential(state: CaseBuilderState, runner: TrcrRunner) -> dict[str, object]:
    current: GraphState = state.to_dict()
    for node in (infer_lanes_node, init_case_node(runner), plan_public_records_node(runner), review_gate_node):
        current.update(node(current))
    current["runner"] = "sequential"
    return dict(current)


def build_case_builder_graph(runner: TrcrRunner):
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError("LangGraph is not installed. Install with `pip install -e '.[agentic]'`.") from exc

    graph = StateGraph(GraphState)
    graph.add_node("infer_lanes", infer_lanes_node)
    graph.add_node("init_case", init_case_node(runner))
    graph.add_node("plan_public_records", plan_public_records_node(runner))
    graph.add_node("review_gate", review_gate_node)
    graph.add_edge(START, "infer_lanes")
    graph.add_edge("infer_lanes", "init_case")
    graph.add_edge("init_case", "plan_public_records")
    graph.add_edge("plan_public_records", "review_gate")
    graph.add_edge("review_gate", END)
    return graph.compile()


def langgraph_available() -> bool:
    try:
        import langgraph  # noqa: F401
    except ImportError:
        return False
    return True
```

- [ ] **Step 4: Rewrite `app/service.py`**

Replace the entire content of `tc-c-kit/src/case_builder/app/service.py` with:

```python
"""Application service boundary for case-builder workflow runs."""

from __future__ import annotations

from typing import Any, Literal

from ..graph.runner import build_case_builder_graph, langgraph_available, run_sequential
from ..models.state import CaseBuilderState
from ..ops.runner import TrcrRunner

RunnerName = Literal["auto", "langgraph", "sequential"]


def run_case_builder(
    state: CaseBuilderState,
    *,
    execute: bool = False,
    runner: RunnerName = "auto",
) -> dict[str, Any]:
    """Run a case-builder plan and return serializable state.

    Dry runs produce the exact TRCR commands the app would execute. Executed
    runs still stop at a human review gate before any narrative use.
    """
    trcr = TrcrRunner(dry_run=not execute)
    if runner in {"auto", "langgraph"} and langgraph_available():
        graph = build_case_builder_graph(trcr)
        result = graph.invoke(state.to_dict())
        result["runner"] = "langgraph"
        return result
    if runner == "langgraph":
        raise RuntimeError("LangGraph is not installed. Install with `pip install -e '.[agentic]'`.")
    return run_sequential(state, trcr)
```

- [ ] **Step 5: Delete the `tools/` package and check for stragglers**

```bash
git rm -r tc-c-kit/src/case_builder/tools
grep -rn "trcr_cli\|CaseBuilderTools\|TrcrToolResult\|case_builder.tools\|from ..tools\|from .tools" tc-c-kit/src tc-c-kit/tests tc-c-kit/docs
```

Expected: `grep` returns no matches in `tc-c-kit/src` and `tc-c-kit/tests`. `tc-c-kit/docs/case-builder-langgraph.md` will still mention `src/case_builder/tools/` — that doc row is updated in Task 9; everything else must be clean. If `grep` finds a code reference this plan missed, update that import to the ops equivalent before proceeding.

- [ ] **Step 6: Run the full suite to verify behavior is preserved**

Run: `cd tc-c-kit && .venv/bin/python -m pytest -q`
Expected: all tests PASS, including `tests/test_case_builder.py` with unchanged assertions (`tool_results` names `init_case` / `plan_public_records`, `dry_run` true, status `waiting_for_human_review`).

- [ ] **Step 7: Commit**

```bash
git add -A tc-c-kit/src/case_builder
git commit -m "refactor(case-builder): re-point graph and service at ops core, drop tools package

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: Re-point CLI local-stack handlers through ops

**Files:**
- Modify: `tc-c-kit/src/case_builder/cli.py` (handlers only; parser definitions unchanged)
- Test: existing `tc-c-kit/tests/test_local_stack.py` plus new assertions appended to it

**Interfaces:**
- Consumes: `source_ops.discover_sources/parse_source/ocr_source`, `query_ops.index_case/query_case` (Tasks 4 and 6).
- Produces: unchanged CLI behavior on success — handlers return the same payload dict that gets `json.dumps`-printed by `main()`. On `ok=False` the handler raises `SystemExit` with the error text (stderr + exit code 1) instead of an unhandled traceback. `remember-research-actions` intentionally keeps calling `case_builder.memory` directly (memory is operational, not a case op — see plan scope note).

- [ ] **Step 1: Write the failing test**

Append to `tc-c-kit/tests/test_local_stack.py`:

```python
def test_cli_parse_source_reports_clean_error_for_non_case(tmp_path, capsys):
    import pytest

    from case_builder.cli import main

    with pytest.raises(SystemExit) as excinfo:
        main(["parse-source", str(tmp_path / "not_a_case"), "S1"])

    assert excinfo.value.code != 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_local_stack.py::test_cli_parse_source_reports_clean_error_for_non_case -v`
Expected: FAIL — currently `CasefileError` propagates as a raw exception, not `SystemExit` (pytest reports `CasefileError`, not the expected `SystemExit`).

- [ ] **Step 3: Update the CLI handlers**

In `tc-c-kit/src/case_builder/cli.py`, replace the imports block:

```python
from .acquisition import discover_sources
from .app.service import run_case_builder
from .memory import remember_research_actions
from .models.state import CaseBuilderState
from .parsing import ocr_source, parse_source
from .retrieval import index_case, query_case
```

with:

```python
from .app.service import run_case_builder
from .memory import remember_research_actions
from .models.state import CaseBuilderState
from .ops import query as query_ops
from .ops import sources as source_ops
from .ops.result import OpResult
```

Add one helper after `main()`:

```python
def unwrap(result: OpResult) -> dict[str, object]:
    if not result.ok:
        raise SystemExit("\n".join(result.errors) or f"{result.name} failed")
    return result.data
```

Replace the five ops-backed handlers (leave `run_plan_command` and `run_remember_command` untouched):

```python
def run_discover_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap(
        source_ops.discover_sources(
            args.case_dir,
            query=args.query,
            searxng_url=args.searxng_url,
            limit=args.limit,
            out=args.out,
        )
    )


def run_parse_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap(source_ops.parse_source(args.case_dir, args.source_id, force=args.force))


def run_ocr_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap(source_ops.ocr_source(args.case_dir, args.source_id, language=args.language, force=args.force))


def run_index_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap(
        query_ops.index_case(
            args.case_dir,
            include_private=args.include_private,
            qdrant_url=args.qdrant_url,
            collection=args.collection,
            embed_model=args.embed_model,
        )
    )


def run_query_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap(
        query_ops.query_case(
            args.case_dir,
            args.query,
            include_private=args.include_private,
            qdrant_url=args.qdrant_url,
            collection=args.collection,
            embed_model=args.embed_model,
            top_k=args.top_k,
        )
    )
```

- [ ] **Step 4: Run tests to verify pass and no regression**

Run: `cd tc-c-kit && .venv/bin/python -m pytest tests/test_local_stack.py tests/test_case_builder.py -v`
Expected: PASS — success-path stdout shape is unchanged (handlers still return the raw payload dict); the new failure-path test passes.

- [ ] **Step 5: Commit**

```bash
git add tc-c-kit/src/case_builder/cli.py tc-c-kit/tests/test_local_stack.py
git commit -m "refactor(cli): route local-stack commands through ops core

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 9: Docs, README map, and final sweep

**Files:**
- Modify: `tc-c-kit/src/case_builder/README.md` (module map: replace the `tools/` row with `ops/`)
- Modify: `tc-c-kit/docs/case-builder-langgraph.md` (Source Layout table)
- Modify: `tc-c-kit/src/case_builder/ops/README.md` (only if module list drifted during implementation)

**Interfaces:**
- Consumes: everything above, finished.
- Produces: accurate docs; a fully green suite; `compileall` clean.

- [ ] **Step 1: Update the Source Layout table in `tc-c-kit/docs/case-builder-langgraph.md`**

Replace the row:

```markdown
| `src/case_builder/tools/` | Repo-local TRCR CLI tool adapter. |
```

with:

```markdown
| `src/case_builder/ops/` | Typed operations core and safety policy shared by CLI, graph nodes, and future MCP frontends. |
```

- [ ] **Step 2: Update `tc-c-kit/src/case_builder/README.md`**

Open the file; wherever it lists or describes `tools/` (module map/table or prose), replace that entry with:

```markdown
| `ops/` | Typed operations core: `OpResult`, `TrcrRunner`, safety `policy`, and per-domain op modules. Frontends call ops instead of `tcr.py` or the ledger. |
```

If the README has no module table, add a short "Module map" section listing `agents/`, `app/`, `graph/`, `models/`, `ops/`, `acquisition/`, `parsing/`, `retrieval/`, `memory/` with one-line descriptions matching each package's own README.

- [ ] **Step 3: Final verification sweep**

```bash
cd tc-c-kit
grep -rn "case_builder.tools\|CaseBuilderTools\|TrcrToolResult" src tests docs README.md; echo "grep exit: $?"
.venv/bin/python -m compileall -q src ../.agents/skills/truecrime-cult-research/scripts
.venv/bin/python ../.agents/skills/truecrime-cult-research/scripts/tcr.py validate data/examples/synthetic_case
.venv/bin/python -m pytest -q
```

Expected: grep exit 1 (no matches), compileall silent, validate reports OK, pytest all green (38 baseline tests + all new ops tests).

- [ ] **Step 4: Commit**

```bash
git add tc-c-kit/src/case_builder/README.md tc-c-kit/docs/case-builder-langgraph.md tc-c-kit/src/case_builder/ops/README.md
git commit -m "docs(case-builder): document ops core module layout

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Self-Review Notes

- **Spec coverage (Phase 1 bullets):** ops extraction → Tasks 1–6; `OpResult` → Task 1; `policy.py` → Task 3; re-point CLI → Task 8; re-point graph nodes → Task 7; safety invariants as tests → Tasks 3 (privacy filter, automation defaults, guilt lint, staged writes), 5 (gated import), 6 (public-safe export defaults, `get_records` filtering). Egress tagging and `remember_research_actions` wrapping are explicitly deferred (Phase 3 dependency / operational-not-case-op) and noted in the plan scope section.
- **Flag accuracy:** all `tcr.py` flags in Tasks 4–6 were verified against `--help` output on 2026-07-01 (`add-source --title/--url/--source-type/--reliability-grade/--no-public-export`, `ingest-url case_dir url` positional, `preserve-source case_dir source_id`, `draft-extraction --template`, `import-extraction case_dir extraction_json`, `link-names --name/--names-file`, `export-* --include-private/--out-dir`, audits take `case_dir`).
- **Type consistency:** `TrcrRunner.run(name, args) -> OpResult` used identically in Tasks 4–6; node factories take `runner: TrcrRunner` in Task 7 matching Task 2's constructor; `merge_result` consumes `OpResult.ok`/`.errors`/`.command`/`.to_dict()` — all defined in Task 1.
- **Behavior preservation:** `test_case_builder.py` and `test_local_stack.py` assertions are never edited (Task 8 only appends a new test); `OpResult.to_dict()` is a superset of `TrcrToolResult.to_dict()` so `tool_results` consumers keep working.
