# tc-c-kit MCP Server (Phase 4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the ops core as an MCP server (`trcr-mcp`, stdio) with three tool tiers — read/query, staged writes, and gated canonical import/exports — plus `trcr://` resources and workflow prompts.

**Architecture:** A `case_builder/mcp/` package built on the official Python MCP SDK's `FastMCP`. Tool logic lives in plain, directly-testable handler functions taking a `ServerContext` (repo root, cases root, non-dry `TrcrRunner`); `register(mcp, ctx)` functions wrap them in typed closures so FastMCP derives schemas from the type hints. Case access goes through `resolve_case(ctx, slug)` (slug allow-list regex + `case.json` existence), so the server never touches arbitrary paths. Every tool returns JSON-serializable dicts derived from `OpResult.to_dict()`; the safety contract stays enforced in ops (gated import requires `confirm=true`; exports default public-safe).

**Tech Stack:** Python ≥3.10; `mcp>=1.2.0` behind a new `[mcp]` extra; console script `trcr-mcp`; pytest (handlers tested directly without the SDK; one in-memory client-session integration test guarded by `importorskip("mcp")` using `asyncio.run`, no pytest-asyncio needed).

## Global Constraints

- Repo root: `/home/jdean/Documents/programming/true-crime-research/tc-c-kit`. All paths relative to it. Run tests with `cd <repo root> && .venv/bin/python -m pytest <path> -v`.
- Modules stay under **200 non-comment LOC**; every package dir under `src/case_builder/` has a `README.md` (enforced by `tests/test_case_builder_structure.py`).
- `[project] dependencies = []` stays empty — the SDK goes in the new `mcp` optional extra. Install with `uv pip install -p .venv/bin/python -e '.[mcp]' -q` (the venv has no pip).
- Spec tool-tier contract: read/query tools never mutate canonical records; `run_report` is treated as safe derived-report generation through `ops.case.report`; staged writes are limited to `staging/`, raw source intake, and source registration; `import_extraction` refuses without `confirm=true` (enforced by `ops.extraction.import_extraction`, already landed); `export_*` accept `include_private` but default public-safe and echo what was filtered.
- No secrets or endpoint config in tool results; Qdrant/SearXNG endpoints come from env or per-call parameters.
- This phase depends only on Phase 1 ops plus `ops.query.get_source_text`. **If Phase 3 has not been executed yet**, first implement `get_source_text` and its tests exactly as specified in Task 1 of `docs/superpowers/plans/2026-07-01-tc-c-kit-llm-agent-nodes.md` (the `record_llm_egress` half may be skipped); if it already exists, verify the signature `get_source_text(case_dir, source_id, *, include_private=False, max_chars=None) -> OpResult` and move on.
- Existing interfaces consumed: `ops.case.case_info / report`, `ops.sources.discover_sources / ingest_url / add_source / parse_source / ocr_source / plan_public_records`, `ops.extraction.draft_extraction / list_packets / read_packet / save_packet / import_extraction`, `ops.query.get_records / query_case / link_names / get_source_text`, `ops.exports.export_manim / export_case_charts / export_analysis_charts`, `ops.runner.TrcrRunner / default_repo_root`, `OpResult`.
- Commit per task, conventional-commit style, ending with:

  ```
  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```

## File Structure (end state)

```
src/case_builder/mcp/
  __init__.py       # empty docstring module (avoid importing the SDK at package import)
  README.md
  context.py        # ServerContext, default_context(), default_skill_root(),
                    # resolve_case(), list_case_slugs()
  tools_read.py     # handlers + register(): case_info, list_cases, get_records,
                    # get_source_text, query_case, list_staged_packets, run_report
  tools_write.py    # handlers + register(): discover_sources, ingest_url, add_source,
                    # parse_source, ocr_source, draft_extraction, save_extraction_packet,
                    # link_names, plan_public_records
  tools_gated.py    # handlers + register(): import_extraction, export_manim,
                    # export_case_charts, export_analysis_charts
  resources.py      # trcr://cases/{case}/..., trcr://references/{name}
  prompts.py        # start_case, process_source, review_packet, public_readiness
  server.py         # create_server(ctx) -> FastMCP, main() stdio entry
pyproject.toml      # MODIFIED: [mcp] extra + trcr-mcp console script
docs/mcp-server.md  # NEW: registration + tool-tier docs
README.md           # MODIFIED: MCP section pointer

New tests:
tests/test_mcp_context.py
tests/test_mcp_tools_read.py
tests/test_mcp_tools_write_gated.py
tests/test_mcp_server.py
```

Out of scope (per spec): HTTP/remote transports (stdio only), skills-doc updates and `lanes.json` (Phase 5), multi-case orchestration.

---

### Dependency Preflight: source-text op

This plan consumes `ops.query.get_source_text`, which may not exist if Phase 3
has not landed yet.

- [ ] **Step 1: Check whether the source-text op already exists**

Run:

```bash
cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit
rg -n "def get_source_text" src/case_builder/ops/query.py tests
```

Expected if Phase 3 landed: at least one implementation hit and one test hit.

- [ ] **Step 2: If missing, land only the source-text shim from Phase 3**

Implement exactly the `get_source_text` tests and `ops.query.get_source_text`
function from Task 1 of
`docs/superpowers/plans/2026-07-01-tc-c-kit-llm-agent-nodes.md`. Skip
`record_llm_egress` and all LLM/graph-node work for this MCP phase.
If a Phase 3 test file such as `tests/test_ops_source_text.py` already exists
and includes `record_llm_egress`, either land the full Phase 3 Task 1 first or
move only the `get_source_text` tests into this preflight; do not leave an
unimplemented LLM-egress assertion in the MCP commit.

Run:

```bash
cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit
.venv/bin/python -m pytest tests/test_ops_query_review_exports.py -v
```

Commit only if the shim was added:

```bash
git add src/case_builder/ops/query.py
git add tests/test_ops_query_review_exports.py
git commit -m "feat(ops): expose registered source text reads

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

If the `get_source_text` tests live in a dedicated file, stage that file instead
of `tests/test_ops_query_review_exports.py`.

---

### Task 1: `[mcp]` extra + server context

**Files:**
- Create: `src/case_builder/mcp/__init__.py`, `src/case_builder/mcp/README.md`, `src/case_builder/mcp/context.py`
- Modify: `pyproject.toml`
- Test: `tests/test_mcp_context.py`

**Interfaces:**
- Consumes: `ops.runner.TrcrRunner`, `ops.runner.default_repo_root`.
- Produces:
  - `@dataclass ServerContext(repo_root: Path, cases_root: Path, runner: TrcrRunner, skill_root: Path | None = None)`
  - `default_context() -> ServerContext` — `cases_root` from `TRCR_CASES_ROOT` env else `<repo_root>/data/cases`; `skill_root` from `TRCR_SKILL_ROOT` env else the repo-local `.agents/skills/truecrime-cult-research` copy; runner is `TrcrRunner(repo_root=repo_root, dry_run=False)`.
  - `default_skill_root(repo_root: Path) -> Path` — prefers `<repo_root>/.agents/skills/truecrime-cult-research`, then the wrapper-level `<repo_root>.parent/.agents/skills/truecrime-cult-research`, so the MCP server and this wrapper checkout both find the installed skill references.
  - `resolve_case(ctx: ServerContext, case: str) -> str` — validates the slug against `CASE_SLUG_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_\-]{0,80}")`, resolves the final path under `cases_root` (rejecting symlink/root escapes), requires `<cases_root>/<case>/case.json` to exist, returns the absolute path string; raises `ValueError` otherwise.
  - `list_case_slugs(ctx) -> list[str]`
  - `error_dict(message: str) -> dict` — `{"ok": False, "errors": [message]}`, the uniform tool-error shape.

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp_context.py`:

```python
from pathlib import Path

import pytest

from case_builder.mcp.context import ServerContext, default_skill_root, error_dict, list_case_slugs, resolve_case
from case_builder.ops.runner import TrcrRunner

KIT_ROOT = Path(__file__).resolve().parents[1]


def make_ctx(cases_root: Path) -> ServerContext:
    return ServerContext(repo_root=KIT_ROOT, cases_root=cases_root, runner=TrcrRunner(repo_root=KIT_ROOT, dry_run=True))


def test_resolve_case_returns_case_path(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    resolved = resolve_case(ctx, "synthetic_case")

    assert resolved == str(synthetic_case_copy)


def test_resolve_case_rejects_traversal_and_unknown(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    for bad in ("../etc", "a/b", "", ".hidden", "no_such_case"):
        with pytest.raises(ValueError):
            resolve_case(ctx, bad)


def test_resolve_case_rejects_symlink_escape(tmp_path):
    cases_root = tmp_path / "cases"
    outside = tmp_path / "outside"
    cases_root.mkdir()
    outside.mkdir()
    (outside / "case.json").write_text("{}", encoding="utf-8")
    (cases_root / "escaped").symlink_to(outside, target_is_directory=True)
    ctx = make_ctx(cases_root)

    with pytest.raises(ValueError):
        resolve_case(ctx, "escaped")


def test_list_case_slugs_finds_only_cases(synthetic_case_copy, tmp_path):
    (synthetic_case_copy.parent / "not_a_case").mkdir()
    ctx = make_ctx(synthetic_case_copy.parent)

    assert list_case_slugs(ctx) == ["synthetic_case"]


def test_default_skill_root_points_at_repo_local_skill():
    assert (default_skill_root(KIT_ROOT) / "SKILL.md").exists()


def test_error_dict_shape():
    assert error_dict("boom") == {"ok": False, "errors": ["boom"]}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_mcp_context.py -v`
Expected: FAIL with `ModuleNotFoundError` for `case_builder.mcp`

- [ ] **Step 3: Write minimal implementation**

Create `src/case_builder/mcp/__init__.py`:

```python
"""MCP server package. Import submodules directly; the SDK loads lazily in server.py."""
```

Create `src/case_builder/mcp/context.py`:

```python
"""Server context: rooted case resolution so tools never touch arbitrary paths."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..ops.runner import TrcrRunner, default_repo_root

CASE_SLUG_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_\-]{0,80}")


@dataclass
class ServerContext:
    repo_root: Path
    cases_root: Path
    runner: TrcrRunner
    skill_root: Path | None = None


def default_context() -> ServerContext:
    repo_root = default_repo_root()
    cases_root = Path(os.environ.get("TRCR_CASES_ROOT") or repo_root / "data" / "cases")
    return ServerContext(
        repo_root=repo_root,
        cases_root=cases_root,
        runner=TrcrRunner(repo_root=repo_root, dry_run=False),
        skill_root=default_skill_root(repo_root),
    )


def default_skill_root(repo_root: Path) -> Path:
    configured = os.environ.get("TRCR_SKILL_ROOT")
    if configured:
        return Path(configured)
    candidates = [
        repo_root / ".agents" / "skills" / "truecrime-cult-research",
        repo_root.parent / ".agents" / "skills" / "truecrime-cult-research",
    ]
    for candidate in candidates:
        if (candidate / "SKILL.md").exists():
            return candidate
    return candidates[0]


def resolve_case(ctx: ServerContext, case: str) -> str:
    if not case or not CASE_SLUG_RE.fullmatch(case):
        raise ValueError(f"Invalid case slug: {case!r}. Use letters, digits, '-' and '_' only.")
    root = ctx.cases_root.resolve()
    path = (root / case).resolve()
    if path.parent != root:
        raise ValueError(f"Case path escapes cases root: {case!r}")
    if not (path / "case.json").exists():
        raise ValueError(f"Unknown case: {case}. Known cases: {', '.join(list_case_slugs(ctx)) or 'none'}")
    return str(path)


def list_case_slugs(ctx: ServerContext) -> list[str]:
    if not ctx.cases_root.exists():
        return []
    root = ctx.cases_root.resolve()
    names = []
    for entry in ctx.cases_root.iterdir():
        resolved = entry.resolve()
        if resolved.parent == root and (resolved / "case.json").exists():
            names.append(entry.name)
    return sorted(names)


def error_dict(message: str) -> dict[str, Any]:
    return {"ok": False, "errors": [message]}
```

Create `src/case_builder/mcp/README.md`:

```markdown
# case_builder.mcp

MCP server over the ops core (stdio, `trcr-mcp`). Tool logic lives in plain
handler functions (`*_tool(ctx, ...)`) so tests call them directly; each
module's `register(mcp, ctx)` wraps them in typed closures for FastMCP schema
generation.

| Module | Responsibility |
| --- | --- |
| `context.py` | `ServerContext`, slug-validated `resolve_case`, uniform `error_dict`. |
| `tools_read.py` | Read/query tier: case info, records, source text, retrieval, packets, report. |
| `tools_write.py` | Staged-write tier: discovery, ingestion, parsing, drafting, packet save, name linking. |
| `tools_gated.py` | Gated tier: `import_extraction` (requires `confirm=true`), public-safe-by-default exports. |
| `resources.py` | `trcr://cases/...` and `trcr://references/...` read-only resources. |
| `prompts.py` | Workflow prompts: start_case, process_source, review_packet, public_readiness. |
| `server.py` | `create_server()` + `main()` stdio entry point. |

The safety contract is enforced in `case_builder.ops` — this package adds no
second enforcement path and must never call `tcr.py` or the ledger directly.
Config: `TRCR_CASES_ROOT` (default `<repo>/data/cases`).
Skill references: `TRCR_SKILL_ROOT` (default repo-local `.agents` skill copy).
```

Update `pyproject.toml` — add the extra (after `llm` if Phase 3 landed, else after `agentic`) and the script:

```toml
mcp = [
  "mcp>=1.2.0",
]
```

```toml
[project.scripts]
trcr-case-builder = "case_builder.cli:main"
trcr-mcp = "case_builder.mcp.server:main"
```

Then install: `uv pip install -p .venv/bin/python -e '.[mcp]' -q`

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_mcp_context.py tests/test_case_builder_structure.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/case_builder/mcp pyproject.toml tests/test_mcp_context.py
git commit -m "feat(mcp): add server context with rooted case resolution

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Read/query tools

**Files:**
- Create: `src/case_builder/mcp/tools_read.py`
- Test: `tests/test_mcp_tools_read.py`

**Interfaces:**
- Consumes: Task 1 context; `ops.case.case_info/report`, `ops.query.get_records/get_source_text/query_case`, `ops.extraction.list_packets`.
- Produces handler functions (all return `dict`):
  - `case_info_tool(ctx, case)` / `list_cases_tool(ctx)` / `list_staged_packets_tool(ctx, case)` / `run_report_tool(ctx, case)`
  - `get_records_tool(ctx, case, record_type, include_private=False, limit=200)` — truncates `records` to `limit` and sets `data["truncated"]=True` when over.
  - `get_source_text_tool(ctx, case, source_id, include_private=False, max_chars=20000)`
  - `query_case_tool(ctx, case, query, include_private=False, top_k=8)` — wraps any exception (missing retrieval extras / Qdrant) into `error_dict`.
  - `register(mcp, ctx)` — registers all of the above as typed MCP tools with docstring descriptions.
  - Convention all handlers follow: slug errors from `resolve_case` are caught and returned as `error_dict(str(exc))`, never raised to the transport.

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp_tools_read.py`:

```python
import json
from pathlib import Path

from case_builder.mcp.context import ServerContext
from case_builder.mcp import tools_read
from case_builder.ops.runner import TrcrRunner

KIT_ROOT = Path(__file__).resolve().parents[1]


def make_ctx(cases_root: Path, dry_run: bool = True) -> ServerContext:
    return ServerContext(repo_root=KIT_ROOT, cases_root=cases_root, runner=TrcrRunner(repo_root=KIT_ROOT, dry_run=dry_run))


def test_case_info_tool_returns_counts(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_read.case_info_tool(ctx, "synthetic_case")

    assert result["ok"] is True
    assert result["data"]["record_counts"]["sources"] >= 1


def test_case_info_tool_reports_unknown_case_as_error_dict(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_read.case_info_tool(ctx, "nope")

    assert result["ok"] is False
    assert "Unknown case" in result["errors"][0]


def test_list_cases_tool(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    assert tools_read.list_cases_tool(ctx) == {"ok": True, "cases": ["synthetic_case"]}


def test_get_records_tool_filters_private_and_truncates(synthetic_case_copy):
    claims = synthetic_case_copy / "records" / "claims.jsonl"
    private_row = {"claim_id": "CPRIV", "claim": "private", "source_ids": ["SDEMO0001"], "public_export": False}
    claims.write_text(claims.read_text(encoding="utf-8") + json.dumps(private_row) + "\n", encoding="utf-8")
    ctx = make_ctx(synthetic_case_copy.parent)

    public = tools_read.get_records_tool(ctx, "synthetic_case", "claims")
    limited = tools_read.get_records_tool(ctx, "synthetic_case", "claims", include_private=True, limit=1)

    assert all(row.get("claim_id") != "CPRIV" for row in public["data"]["records"])
    assert len(limited["data"]["records"]) == 1
    assert limited["data"]["truncated"] is True


def test_run_report_tool_plans_report_command(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_read.run_report_tool(ctx, "synthetic_case")

    assert result["command"][2] == "report"


def test_query_case_tool_degrades_to_error_dict(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_read.query_case_tool(ctx, "synthetic_case", "what claims lack spans?")

    # Retrieval extras/Qdrant are absent in CI: must be a structured error, not a raise.
    assert isinstance(result, dict)
    assert "ok" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_mcp_tools_read.py -v`
Expected: FAIL with `ImportError` for `tools_read`

- [ ] **Step 3: Write minimal implementation**

Create `src/case_builder/mcp/tools_read.py`:

```python
"""Read/query tool tier: always available, never writes."""

from __future__ import annotations

from typing import Any

from ..ops import case as case_ops
from ..ops import extraction as extraction_ops
from ..ops import query as query_ops
from .context import ServerContext, error_dict, list_case_slugs, resolve_case


def case_info_tool(ctx: ServerContext, case: str) -> dict[str, Any]:
    try:
        return case_ops.case_info(resolve_case(ctx, case)).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))


def list_cases_tool(ctx: ServerContext) -> dict[str, Any]:
    return {"ok": True, "cases": list_case_slugs(ctx)}


def get_records_tool(
    ctx: ServerContext, case: str, record_type: str, include_private: bool = False, limit: int = 200
) -> dict[str, Any]:
    try:
        result = query_ops.get_records(resolve_case(ctx, case), record_type, include_private=include_private)
    except ValueError as exc:
        return error_dict(str(exc))
    if result.ok and limit and len(result.data["records"]) > limit:
        result.data["records"] = result.data["records"][:limit]
        result.data["truncated"] = True
    return result.to_dict()


def get_source_text_tool(
    ctx: ServerContext, case: str, source_id: str, include_private: bool = False, max_chars: int = 20000
) -> dict[str, Any]:
    try:
        return query_ops.get_source_text(
            resolve_case(ctx, case), source_id, include_private=include_private, max_chars=max_chars
        ).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))


def query_case_tool(
    ctx: ServerContext, case: str, query: str, include_private: bool = False, top_k: int = 8
) -> dict[str, Any]:
    try:
        return query_ops.query_case(
            resolve_case(ctx, case), query, include_private=include_private, top_k=top_k
        ).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))
    except Exception as exc:  # retrieval extras or Qdrant may be absent
        return error_dict(f"query_case failed: {exc}")


def list_staged_packets_tool(ctx: ServerContext, case: str) -> dict[str, Any]:
    try:
        return extraction_ops.list_packets(resolve_case(ctx, case)).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))


def run_report_tool(ctx: ServerContext, case: str) -> dict[str, Any]:
    try:
        return case_ops.report(ctx.runner, resolve_case(ctx, case)).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))


def register(mcp: Any, ctx: ServerContext) -> None:
    @mcp.tool()
    def case_info(case: str) -> dict:
        """Case metadata and per-record-type counts for a TRCR case slug."""
        return case_info_tool(ctx, case)

    @mcp.tool()
    def list_cases() -> dict:
        """List available TRCR case slugs."""
        return list_cases_tool(ctx)

    @mcp.tool()
    def get_records(case: str, record_type: str, include_private: bool = False, limit: int = 200) -> dict:
        """Read ledger records (sources, entities, claims, events, ...). Private records excluded unless include_private."""
        return get_records_tool(ctx, case, record_type, include_private, limit)

    @mcp.tool()
    def get_source_text(case: str, source_id: str, include_private: bool = False, max_chars: int = 20000) -> dict:
        """Read the extracted text of a registered source."""
        return get_source_text_tool(ctx, case, source_id, include_private, max_chars)

    @mcp.tool()
    def query_case(case: str, query: str, include_private: bool = False, top_k: int = 8) -> dict:
        """Semantic retrieval over the local case evidence index (requires local Qdrant stack)."""
        return query_case_tool(ctx, case, query, include_private, top_k)

    @mcp.tool()
    def list_staged_packets(case: str) -> dict:
        """List extraction packets staged for human review."""
        return list_staged_packets_tool(ctx, case)

    @mcp.tool()
    def run_report(case: str) -> dict:
        """Write the case evidence-board Markdown report."""
        return run_report_tool(ctx, case)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_mcp_tools_read.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/case_builder/mcp/tools_read.py tests/test_mcp_tools_read.py
git commit -m "feat(mcp): add read/query tool tier

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Staged-write + gated tools

**Files:**
- Create: `src/case_builder/mcp/tools_write.py`
- Create: `src/case_builder/mcp/tools_gated.py`
- Test: `tests/test_mcp_tools_write_gated.py`

**Interfaces:**
- Consumes: ops functions listed in Global Constraints; `resolve_case` / `error_dict`.
- Produces:
  - `tools_write` handlers: `discover_sources_tool(ctx, case, query, limit=10)`, `ingest_url_tool(ctx, case, url, title=None, source_type=None, reliability_grade=None)`, `add_source_tool(ctx, case, title, url=None, source_type=None, reliability_grade=None)`, `parse_source_tool(ctx, case, source_id)`, `ocr_source_tool(ctx, case, source_id, language="eng")`, `draft_extraction_tool(ctx, case, source_id, template="generic")`, `save_extraction_packet_tool(ctx, case, packet_name, packet: dict)`, `link_names_tool(ctx, case, names: list[str])`, `plan_public_records_tool(ctx, case, subject, lanes: list[str] | None = None)`, plus `register(mcp, ctx)`.
  - `tools_gated` handlers: `import_extraction_tool(ctx, case, packet, confirm=False)` (rejects packet names containing `/`; builds the staged path itself), `export_manim_tool(ctx, case, include_private=False)`, `export_case_charts_tool(...)`, `export_analysis_charts_tool(...)` — each export result carries `data["privacy"]` echoing the filter mode; plus `register(mcp, ctx)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp_tools_write_gated.py`:

```python
from pathlib import Path

from case_builder.mcp.context import ServerContext
from case_builder.mcp import tools_gated, tools_write
from case_builder.ops.runner import TrcrRunner

KIT_ROOT = Path(__file__).resolve().parents[1]


def make_ctx(cases_root: Path) -> ServerContext:
    return ServerContext(repo_root=KIT_ROOT, cases_root=cases_root, runner=TrcrRunner(repo_root=KIT_ROOT, dry_run=True))


def test_save_extraction_packet_stages_json(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)
    packet = {"source_id": "SDEMO0001", "entities": [{"name": "A Witness", "role": "witness", "source_ids": ["SDEMO0001"]}]}

    result = tools_write.save_extraction_packet_tool(ctx, "synthetic_case", "SDEMO0001_extraction.json", packet)

    assert result["ok"] is True
    assert (synthetic_case_copy / "staging" / "extractions" / "SDEMO0001_extraction.json").exists()


def test_save_extraction_packet_rejects_guilt_labels(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)
    packet = {"entities": [{"name": "A Person", "role": "suspect"}]}

    result = tools_write.save_extraction_packet_tool(ctx, "synthetic_case", "bad.json", packet)

    assert result["ok"] is False


def test_ingest_url_tool_builds_command(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_write.ingest_url_tool(ctx, "synthetic_case", "https://example.com/story", source_type="news_article")

    assert result["command"][2] == "ingest-url"


def test_import_extraction_refuses_without_confirm(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_gated.import_extraction_tool(ctx, "synthetic_case", "p.json")

    assert result["ok"] is False
    assert any("confirm" in error for error in result["errors"])


def test_import_extraction_rejects_path_like_packet_names(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_gated.import_extraction_tool(ctx, "synthetic_case", "../records/claims.jsonl", confirm=True)

    assert result["ok"] is False


def test_import_extraction_plans_command_with_confirm(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    result = tools_gated.import_extraction_tool(ctx, "synthetic_case", "p.json", confirm=True)

    assert result["ok"] is True
    assert result["command"][2] == "import-extraction"
    assert result["command"][4].endswith("staging/extractions/p.json")


def test_exports_echo_privacy_mode(synthetic_case_copy):
    ctx = make_ctx(synthetic_case_copy.parent)

    public = tools_gated.export_manim_tool(ctx, "synthetic_case")
    internal = tools_gated.export_manim_tool(ctx, "synthetic_case", include_private=True)

    assert "--include-private" not in public["command"]
    assert "excluded" in public["data"]["privacy"]
    assert "--include-private" in internal["command"]
    assert "internal review" in internal["data"]["privacy"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_mcp_tools_write_gated.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

Create `src/case_builder/mcp/tools_write.py`:

```python
"""Staged-write tool tier: writes land only under staging/ (enforced by ops)."""

from __future__ import annotations

from typing import Any

from ..ops import extraction as extraction_ops
from ..ops import query as query_ops
from ..ops import sources as source_ops
from .context import ServerContext, error_dict, resolve_case


def discover_sources_tool(ctx: ServerContext, case: str, query: str, limit: int = 10) -> dict[str, Any]:
    try:
        return source_ops.discover_sources(resolve_case(ctx, case), query=query, limit=limit).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))
    except Exception as exc:  # SearXNG may be down/unconfigured
        return error_dict(f"discover_sources failed: {exc}")


def ingest_url_tool(
    ctx: ServerContext,
    case: str,
    url: str,
    title: str | None = None,
    source_type: str | None = None,
    reliability_grade: str | None = None,
) -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return source_ops.ingest_url(
        ctx.runner, case_dir, url, title=title, source_type=source_type, reliability_grade=reliability_grade
    ).to_dict()


def add_source_tool(
    ctx: ServerContext,
    case: str,
    title: str,
    url: str | None = None,
    source_type: str | None = None,
    reliability_grade: str | None = None,
) -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return source_ops.add_source(
        ctx.runner, case_dir, title=title, url=url, source_type=source_type, reliability_grade=reliability_grade
    ).to_dict()


def parse_source_tool(ctx: ServerContext, case: str, source_id: str) -> dict[str, Any]:
    try:
        return source_ops.parse_source(resolve_case(ctx, case), source_id).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))
    except RuntimeError as exc:  # Docling missing or no raw file
        return error_dict(str(exc))


def ocr_source_tool(ctx: ServerContext, case: str, source_id: str, language: str = "eng") -> dict[str, Any]:
    try:
        return source_ops.ocr_source(resolve_case(ctx, case), source_id, language=language).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))
    except RuntimeError as exc:
        return error_dict(str(exc))


def draft_extraction_tool(ctx: ServerContext, case: str, source_id: str, template: str = "generic") -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return extraction_ops.draft_extraction(ctx.runner, case_dir, source_id, template=template).to_dict()


def save_extraction_packet_tool(ctx: ServerContext, case: str, packet_name: str, packet: dict) -> dict[str, Any]:
    try:
        return extraction_ops.save_packet(resolve_case(ctx, case), packet_name, packet).to_dict()
    except ValueError as exc:
        return error_dict(str(exc))


def link_names_tool(ctx: ServerContext, case: str, names: list[str]) -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return query_ops.link_names(ctx.runner, case_dir, names=names).to_dict()


def plan_public_records_tool(ctx: ServerContext, case: str, subject: str, lanes: list[str] | None = None) -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return source_ops.plan_public_records(ctx.runner, case_dir, subject, lanes or []).to_dict()


def register(mcp: Any, ctx: ServerContext) -> None:
    @mcp.tool()
    def discover_sources(case: str, query: str, limit: int = 10) -> dict:
        """Search local SearXNG for lead-only source candidates (staged, never evidence)."""
        return discover_sources_tool(ctx, case, query, limit)

    @mcp.tool()
    def ingest_url(case: str, url: str, title: str | None = None, source_type: str | None = None, reliability_grade: str | None = None) -> dict:
        """Fetch a public URL, extract text, and register it as a source."""
        return ingest_url_tool(ctx, case, url, title, source_type, reliability_grade)

    @mcp.tool()
    def add_source(case: str, title: str, url: str | None = None, source_type: str | None = None, reliability_grade: str | None = None) -> dict:
        """Register a source manually with publication metadata."""
        return add_source_tool(ctx, case, title, url, source_type, reliability_grade)

    @mcp.tool()
    def parse_source(case: str, source_id: str) -> dict:
        """Parse a registered source's raw file to text with Docling."""
        return parse_source_tool(ctx, case, source_id)

    @mcp.tool()
    def ocr_source(case: str, source_id: str, language: str = "eng") -> dict:
        """OCR a registered PDF source with OCRmyPDF."""
        return ocr_source_tool(ctx, case, source_id, language)

    @mcp.tool()
    def draft_extraction(case: str, source_id: str, template: str = "generic") -> dict:
        """Create a structured extraction packet template for a source in staging/."""
        return draft_extraction_tool(ctx, case, source_id, template)

    @mcp.tool()
    def save_extraction_packet(case: str, packet_name: str, packet: dict) -> dict:
        """Save a filled extraction packet to staging/ (guilt-label lint enforced; not a canonical import)."""
        return save_extraction_packet_tool(ctx, case, packet_name, packet)

    @mcp.tool()
    def link_names(case: str, names: list[str]) -> dict:
        """Link names to existing events/co-mentions (private-by-default, no guilt inference)."""
        return link_names_tool(ctx, case, names)

    @mcp.tool()
    def plan_public_records(case: str, subject: str, lanes: list[str] | None = None) -> dict:
        """Write a public-record source-lane plan for a subject into staging/candidates/."""
        return plan_public_records_tool(ctx, case, subject, lanes)
```

Create `src/case_builder/mcp/tools_gated.py`:

```python
"""Gated tool tier: canonical import and public exports."""

from __future__ import annotations

from typing import Any

from ..ops import exports as export_ops
from ..ops import extraction as extraction_ops
from .context import ServerContext, error_dict, resolve_case

PUBLIC_NOTE = "public-safe: records with public_export=false were excluded"
PRIVATE_NOTE = "include_private=true: for internal review only, do not publish"


def import_extraction_tool(ctx: ServerContext, case: str, packet: str, confirm: bool = False) -> dict[str, Any]:
    if "/" in packet or "\\" in packet or packet.startswith("."):
        return error_dict(f"Packet must be a bare filename under staging/extractions/, got: {packet!r}")
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    packet_path = f"{case_dir.rstrip('/')}/staging/extractions/{packet}"
    return extraction_ops.import_extraction(ctx.runner, case_dir, packet_path, confirm=confirm).to_dict()


def _export(result, include_private: bool) -> dict[str, Any]:
    payload = result.to_dict()
    payload.setdefault("data", {})
    payload["data"]["privacy"] = PRIVATE_NOTE if include_private else PUBLIC_NOTE
    return payload


def export_manim_tool(ctx: ServerContext, case: str, include_private: bool = False) -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return _export(export_ops.export_manim(ctx.runner, case_dir, include_private=include_private), include_private)


def export_case_charts_tool(ctx: ServerContext, case: str, include_private: bool = False) -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return _export(export_ops.export_case_charts(ctx.runner, case_dir, include_private=include_private), include_private)


def export_analysis_charts_tool(ctx: ServerContext, case: str, include_private: bool = False) -> dict[str, Any]:
    try:
        case_dir = resolve_case(ctx, case)
    except ValueError as exc:
        return error_dict(str(exc))
    return _export(
        export_ops.export_analysis_charts(ctx.runner, case_dir, include_private=include_private), include_private
    )


def register(mcp: Any, ctx: ServerContext) -> None:
    @mcp.tool()
    def import_extraction(case: str, packet: str, confirm: bool = False) -> dict:
        """Import a staged extraction packet into canonical records.

        GATED: requires confirm=true. Only set confirm=true after the user has
        explicitly reviewed this packet and approved the import in conversation.
        """
        return import_extraction_tool(ctx, case, packet, confirm)

    @mcp.tool()
    def export_manim(case: str, include_private: bool = False) -> dict:
        """Export public-safe Manim CSVs. include_private is for internal review only."""
        return export_manim_tool(ctx, case, include_private)

    @mcp.tool()
    def export_case_charts(case: str, include_private: bool = False) -> dict:
        """Export the people graph and subcase timeline charts (public-safe by default)."""
        return export_case_charts_tool(ctx, case, include_private)

    @mcp.tool()
    def export_analysis_charts(case: str, include_private: bool = False) -> dict:
        """Export the extended analysis chart package (public-safe by default)."""
        return export_analysis_charts_tool(ctx, case, include_private)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_mcp_tools_write_gated.py tests/test_case_builder_structure.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/case_builder/mcp/tools_write.py src/case_builder/mcp/tools_gated.py tests/test_mcp_tools_write_gated.py
git commit -m "feat(mcp): add staged-write and gated tool tiers

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Resources + prompts

**Files:**
- Create: `src/case_builder/mcp/resources.py`
- Create: `src/case_builder/mcp/prompts.py`
- Test: appended to `tests/test_mcp_tools_read.py`

**Interfaces:**
- Consumes: `resolve_case`, `ops.query.get_records`, `ops.extraction.read_packet`.
- Produces:
  - `resources.py`: handler functions `case_json_resource(ctx, case) -> str`, `records_resource(ctx, case, record_type) -> str` (public-safe JSONL), `packet_resource(ctx, case, name) -> str`, `reference_resource(ctx, name) -> str` (allow-list: `controlled_vocabularies`, `topic_extraction_templates`; reads `<skill_root>/references/<name>.md`); plus `register(mcp, ctx)` binding URI templates `trcr://cases/{case}/case.json`, `trcr://cases/{case}/records/{record_type}`, `trcr://cases/{case}/staging/extractions/{name}`, `trcr://references/{name}`.
  - `prompts.py`: `register(mcp, ctx)` defining four `@mcp.prompt()` functions — `start_case`, `process_source`, `review_packet`, `public_readiness` — each returning a workflow-instruction string; the module exposes the raw strings as constants (`START_CASE`, `PROCESS_SOURCE`, `REVIEW_PACKET`, `PUBLIC_READINESS`) so tests assert content without the SDK.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_mcp_tools_read.py`:

```python
def test_records_resource_is_public_safe_jsonl(synthetic_case_copy):
    import json as json_module

    from case_builder.mcp import resources

    claims = synthetic_case_copy / "records" / "claims.jsonl"
    private_row = {"claim_id": "CPRIV2", "claim": "private", "source_ids": ["SDEMO0001"], "public_export": False}
    claims.write_text(claims.read_text(encoding="utf-8") + json_module.dumps(private_row) + "\n", encoding="utf-8")
    ctx = make_ctx(synthetic_case_copy.parent)

    text = resources.records_resource(ctx, "synthetic_case", "claims")

    assert "CPRIV2" not in text
    assert text.strip()  # public rows still present


def test_reference_resource_allow_list(synthetic_case_copy):
    import pytest

    from case_builder.mcp import resources

    ctx = make_ctx(synthetic_case_copy.parent)

    vocab = resources.reference_resource(ctx, "controlled_vocabularies")
    assert vocab.strip()

    with pytest.raises(ValueError):
        resources.reference_resource(ctx, "../SKILL")


def test_prompts_cover_safety_workflow():
    from case_builder.mcp import prompts

    assert "review" in prompts.REVIEW_PACKET.lower()
    assert "confirm" in prompts.REVIEW_PACKET.lower()
    assert "privacy" in prompts.PUBLIC_READINESS.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_mcp_tools_read.py -v`
Expected: new tests FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

Create `src/case_builder/mcp/resources.py`:

```python
"""Read-only trcr:// resources for cheap case context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..ops import extraction as extraction_ops
from ..ops import query as query_ops
from .context import ServerContext, default_skill_root, resolve_case

REFERENCE_ALLOW_LIST = frozenset({"controlled_vocabularies", "topic_extraction_templates"})


def case_json_resource(ctx: ServerContext, case: str) -> str:
    return (Path(resolve_case(ctx, case)) / "case.json").read_text(encoding="utf-8")


def records_resource(ctx: ServerContext, case: str, record_type: str) -> str:
    result = query_ops.get_records(resolve_case(ctx, case), record_type)
    if not result.ok:
        raise ValueError("; ".join(result.errors))
    rows = result.data.get("records", [])
    return "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)


def packet_resource(ctx: ServerContext, case: str, name: str) -> str:
    result = extraction_ops.read_packet(resolve_case(ctx, case), name)
    if not result.ok:
        raise ValueError("; ".join(result.errors))
    return json.dumps(result.data["packet"], ensure_ascii=False, indent=2, sort_keys=True)


def reference_resource(ctx: ServerContext, name: str) -> str:
    if name not in REFERENCE_ALLOW_LIST:
        raise ValueError(f"Unknown reference: {name!r}. Available: {', '.join(sorted(REFERENCE_ALLOW_LIST))}")
    skill_root = ctx.skill_root or default_skill_root(ctx.repo_root)
    return (skill_root / "references" / f"{name}.md").read_text(encoding="utf-8")


def register(mcp: Any, ctx: ServerContext) -> None:
    @mcp.resource("trcr://cases/{case}/case.json")
    def case_json(case: str) -> str:
        """Case metadata JSON."""
        return case_json_resource(ctx, case)

    @mcp.resource("trcr://cases/{case}/records/{record_type}")
    def records(case: str, record_type: str) -> str:
        """Public-safe JSONL rows for one record type."""
        return records_resource(ctx, case, record_type)

    @mcp.resource("trcr://cases/{case}/staging/extractions/{name}")
    def packet(case: str, name: str) -> str:
        """A staged extraction packet awaiting review."""
        return packet_resource(ctx, case, name)

    @mcp.resource("trcr://references/{name}")
    def reference(name: str) -> str:
        """Skill reference documents (controlled vocabularies, extraction templates)."""
        return reference_resource(ctx, name)
```

Note: FastMCP maps URI template variables to function parameters by name —
each resource function's parameters must exactly match its template variables
(`case`, `record_type`, `name`), or registration fails.

Create `src/case_builder/mcp/prompts.py`:

```python
"""Workflow prompts so any MCP host receives the skill guidance in-band."""

from __future__ import annotations

from typing import Any

from .context import ServerContext

START_CASE = """Start a TRCR research case. Steps:
1. Confirm the case slug and title with the user, then check list_cases / case_info.
2. Plan source lanes with plan_public_records for the seed subject.
3. Capture public sources with ingest_url or add_source; grade reliability honestly.
Safety: public-interest sources only; no guilt/membership inference from proximity;
private-person details stay private by default; every claim needs a traceable source.
"""

PROCESS_SOURCE = """Process one registered source end to end:
1. parse_source (or ocr_source for scanned PDFs) to get text.
2. draft_extraction to create the packet template; read the source text with get_source_text.
3. Fill the packet: only what the source itself states, with source_ids on every record,
   assertion_type preserved, neutral role labels, status unverified.
4. save_extraction_packet, then ask the user to review it. Do NOT import it yourself.
"""

REVIEW_PACKET = """Help the user review a staged extraction packet before canonical import:
1. list_staged_packets, then read the packet resource and its source text side by side.
2. Check every record: correct source_ids, no invented facts, neutral labels, privacy flags.
3. Only after the user explicitly approves in conversation, call import_extraction with
   confirm=true. Never set confirm=true on your own initiative.
"""

PUBLIC_READINESS = """Assess public-output readiness:
1. run_report and get_records to survey claims, statuses, and confidence.
2. Check contradiction, source-independence, and privacy posture; wire stories that share
   an independence_group are one source, not corroboration.
3. Summarize blockers for the user. Exports default public-safe; include_private is for
   internal review only and its output must not be published.
"""


def register(mcp: Any, ctx: ServerContext) -> None:
    @mcp.prompt()
    def start_case() -> str:
        """Start a new TRCR case with safe source planning."""
        return START_CASE

    @mcp.prompt()
    def process_source() -> str:
        """Parse, draft, and fill one source's extraction packet."""
        return PROCESS_SOURCE

    @mcp.prompt()
    def review_packet() -> str:
        """Review a staged packet and gate the canonical import."""
        return REVIEW_PACKET

    @mcp.prompt()
    def public_readiness() -> str:
        """Audit public-output readiness and privacy posture."""
        return PUBLIC_READINESS
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_mcp_tools_read.py tests/test_case_builder_structure.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/case_builder/mcp/resources.py src/case_builder/mcp/prompts.py tests/test_mcp_tools_read.py
git commit -m "feat(mcp): add trcr:// resources and workflow prompts

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Server assembly + in-memory integration test

**Files:**
- Create: `src/case_builder/mcp/server.py`
- Test: `tests/test_mcp_server.py`

**Interfaces:**
- Consumes: all `register(mcp, ctx)` functions from Tasks 2–4, `default_context()`.
- Produces: `create_server(ctx: ServerContext | None = None) -> FastMCP` and `main() -> int` (stdio `run()`), wired to the `trcr-mcp` console script from Task 1.

- [ ] **Step 1: Write the integration test**

Create `tests/test_mcp_server.py`:

```python
import asyncio
import json
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from case_builder.mcp.context import ServerContext
from case_builder.mcp.server import create_server
from case_builder.ops.runner import TrcrRunner

KIT_ROOT = Path(__file__).resolve().parents[1]


def make_server(cases_root: Path):
    ctx = ServerContext(repo_root=KIT_ROOT, cases_root=cases_root, runner=TrcrRunner(repo_root=KIT_ROOT, dry_run=True))
    return create_server(ctx)


def low_level_server(server):
    return getattr(server, "_mcp_server", None) or server.mcp_server


def tool_payload(result) -> dict:
    return json.loads(result.content[0].text)


def test_server_exposes_tools_and_enforces_gate(synthetic_case_copy):
    from mcp.shared.memory import create_connected_server_and_client_session as client_session

    server = make_server(synthetic_case_copy.parent)

    async def scenario():
        async with client_session(low_level_server(server)) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            assert {"case_info", "get_records", "save_extraction_packet", "import_extraction", "export_manim"} <= names

            info = tool_payload(await client.call_tool("case_info", {"case": "synthetic_case"}))
            assert info["ok"] is True

            refusal = tool_payload(
                await client.call_tool("import_extraction", {"case": "synthetic_case", "packet": "p.json"})
            )
            assert refusal["ok"] is False

            prompts = await client.list_prompts()
            assert {"start_case", "process_source", "review_packet", "public_readiness"} <= {
                prompt.name for prompt in prompts.prompts
            }

    asyncio.run(scenario())
```

Note: `create_connected_server_and_client_session` takes the low-level
`mcp.server.lowlevel.Server`; FastMCP wraps one (attribute `_mcp_server` in the
official SDK). If the SDK version renames it, `low_level_server` covers the
`mcp_server` spelling; if both attributes are missing, check
`.venv/lib/python*/site-packages/mcp/server/fastmcp/server.py` for the wrapped
server attribute and update `low_level_server` — do not weaken the test.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_mcp_server.py -v`
Expected: FAIL with `ImportError` for `case_builder.mcp.server` (or SKIP if the `[mcp]` extra was not installed — install it per Task 1 before proceeding)

- [ ] **Step 3: Write minimal implementation**

Create `src/case_builder/mcp/server.py`:

```python
"""FastMCP server assembly and stdio entry point."""

from __future__ import annotations

from . import prompts, resources, tools_gated, tools_read, tools_write
from .context import ServerContext, default_context

SERVER_INSTRUCTIONS = """TRCR case-builder MCP server for public-interest true-crime research.

Tool tiers: read/query tools are always safe; write tools stage drafts under
staging/ only; import_extraction is GATED — it writes canonical records and
must only run with confirm=true after explicit user approval. Exports default
public-safe; include_private output is for internal review and must not be
published. Never infer guilt, membership, or motive from proximity; every
claim needs a traceable source.
"""


def create_server(ctx: ServerContext | None = None):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "The MCP server requires the mcp extra. Install with "
            "`uv pip install -p .venv/bin/python -e '.[mcp]'`."
        ) from exc
    context = ctx or default_context()
    mcp = FastMCP("trcr-case-builder", instructions=SERVER_INSTRUCTIONS)
    tools_read.register(mcp, context)
    tools_write.register(mcp, context)
    tools_gated.register(mcp, context)
    resources.register(mcp, context)
    prompts.register(mcp, context)
    return mcp


def main() -> int:
    create_server().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit && .venv/bin/python -m pytest tests/test_mcp_server.py -v && .venv/bin/python -c "from case_builder.mcp.server import create_server; create_server()" && echo "server builds"`
Expected: test PASS; `server builds`

- [ ] **Step 5: Commit**

```bash
git add src/case_builder/mcp/server.py tests/test_mcp_server.py
git commit -m "feat(mcp): assemble trcr-mcp server with stdio entry point

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Docs + final sweep

**Files:**
- Create: `docs/mcp-server.md`
- Modify: `README.md` (add MCP section after the "LangGraph case-builder bootstrap" section)

- [ ] **Step 1: Write `docs/mcp-server.md`**

````markdown
# TRCR MCP Server

`trcr-mcp` exposes the case-builder ops core to MCP hosts (Claude Code, Codex,
Claude Desktop) over stdio.

## Install and register

```bash
uv pip install -p .venv/bin/python -e '.[mcp]'

# Claude Code:
claude mcp add trcr -- /home/jdean/Documents/programming/true-crime-research/tc-c-kit/.venv/bin/trcr-mcp

# Any other host: command `/home/jdean/Documents/programming/true-crime-research/tc-c-kit/.venv/bin/trcr-mcp`,
# transport stdio.
# If your shell has the venv activated, `trcr-mcp` is equivalent.
# Optional env: TRCR_CASES_ROOT (default <repo>/data/cases),
# TRCR_SKILL_ROOT (default repo-local .agents skill copy),
# TRCR_MODEL / Qdrant / SearXNG settings come from the environment as usual.
```

## Tool tiers

| Tier | Tools | Writes |
| --- | --- | --- |
| Read/query/report | `case_info`, `list_cases`, `get_records`, `get_source_text`, `query_case`, `list_staged_packets`, `run_report` | none for canonical records; `run_report` may write a derived evidence-board export |
| Staged write | `discover_sources`, `ingest_url`, `add_source`, `parse_source`, `ocr_source`, `draft_extraction`, `save_extraction_packet`, `link_names`, `plan_public_records` | `staging/`, `raw/`, source registry |
| Gated | `import_extraction` (**requires `confirm=true` after explicit user approval**), `export_manim`, `export_case_charts`, `export_analysis_charts` (public-safe by default; `include_private` echoes an internal-review warning) | canonical records / exports |

## Resources and prompts

Resources: `trcr://cases/{case}/case.json`, `trcr://cases/{case}/records/{record_type}`
(public-safe JSONL), `trcr://cases/{case}/staging/extractions/{name}`,
`trcr://references/{controlled_vocabularies|topic_extraction_templates}`.

Prompts: `start_case`, `process_source`, `review_packet`, `public_readiness` —
the skill workflow guidance for hosts without repo-local skills.

## Safety

The safety contract lives in `case_builder.ops` (staged-write classification,
privacy filtering, guilt-label lint, gated import); the server adds slug-rooted
case resolution and never touches `tcr.py` or ledger files directly. Records
with `public_export: false` never appear in default reads, resources, or
exports.
````

- [ ] **Step 2: Add the README section**

Insert into `README.md` after the LangGraph case-builder section:

````markdown
## MCP server

Expose the same ops surface to Claude Code, Codex, or Claude Desktop:

```bash
uv pip install -p .venv/bin/python -e '.[mcp]'
claude mcp add trcr -- /home/jdean/Documents/programming/true-crime-research/tc-c-kit/.venv/bin/trcr-mcp
```

Read/query tools are always safe; write tools stage drafts only; canonical
`import_extraction` requires `confirm=true` after explicit human review, and
exports stay public-safe by default. See `docs/mcp-server.md`.
````

- [ ] **Step 3: Final verification sweep**

```bash
cd /home/jdean/Documents/programming/true-crime-research/tc-c-kit
.venv/bin/python -m compileall -q src
.venv/bin/python -m pytest -q
grep -rn "tcr.py\|records/.*jsonl" src/case_builder/mcp --include="*.py" | grep -v "staging" ; echo "grep exit: $?"
```

Expected: compileall silent; full suite green; grep exit 1 (the MCP package has no direct `tcr.py` or ledger-file access).

- [ ] **Step 4: Commit**

```bash
git add docs/mcp-server.md README.md
git commit -m "docs(mcp): document server registration, tool tiers, and safety

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Self-Review Notes

- **Spec coverage (Phase 4 / Component 5):** FastMCP + stdio + `trcr-mcp` + `[mcp]` extra → Tasks 1, 5; read/query/report tool list → Task 2 (all seven named tools, with `run_report` treated as derived export generation rather than canonical mutation); staged-write tool list → Task 3 (`tools_write`, including `plan_public_records` which the spec's skill routing relies on); gated `import_extraction(confirm)` with instructive description + `export_*` echoing the privacy filter → Task 3; resources incl. vocabularies/templates → Task 4; four prompts → Task 4; audit logging remains owned by ops for operations that write research actions; read-only tools are not forced to synthesize audit rows; "no secrets in tool results" — handlers pass no endpoint config and `OpResult` carries only command/output data.
- **Deviation noted:** spec's resource list mentions records and packets; this plan serves records public-safe-only through resources (private rows require the `get_records` tool with `include_private=true`), which is the stricter reading and is documented in Task 6.
- **Type consistency:** `ServerContext` fields and `resolve_case(ctx, case) -> str` match across Tasks 1–5; every handler returns `dict`; `error_dict` shape `{"ok": False, "errors": [...]}` matches `OpResult.to_dict()`'s failure keys so hosts see one error shape; the Task 5 test's tool names match the `register` closures in Tasks 2–3.
- **Placeholder scan:** no TBDs or intentionally-wrong code variants remain.
