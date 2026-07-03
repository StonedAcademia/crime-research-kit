# CLI + Acquisition Swaps Implementation Plan (Stage 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `urllib.request` with `httpx` (timeouts, redirects, bounded retries) in acquisition, and migrate both argparse CLIs to typer while preserving every command name, argument, and flag verbatim — enforced by a frozen CLI-surface snapshot.

**Architecture:** Handlers keep their `(args: argparse.Namespace)` signatures; typer commands are thin wrappers that collect typed parameters, build a `Namespace`, and call the existing handler. Before any migration, the current argparse surface is introspected into `docs/guides/cli-surface.json`; a governance test then introspects the typer apps (via their click commands) and asserts the surface is identical. `crk-ledger`'s 25 commands split into four group modules under a new `commands/` package to respect the 200-LOC ceiling.

**Tech Stack:** httpx ≥0.27, typer ≥0.12 (both already required deps from stage 1), click introspection, pytest.

**Spec:** `docs/superpowers/specs/2026-07-02-src-skills-stabilization-design.md` (Stage 3 section). Depends on stage 1 (merged); independent of stage 2.

**Recorded decision:** wrapper-style migration (Namespace bridge) over rewriting ~28 handler functions to typed parameters. Rationale: the spec's hard requirement is "every existing command name, argument, and flag signature is preserved verbatim so skills, docs, and muscle memory need no changes"; the bridge bounds the diff to the CLI layer and the snapshot test proves preservation. Converting handlers to typed params is a possible later cleanup, not this stage.

## Global Constraints

- Branch: `refactor/typer-httpx`, cut from `dev`.
- Every command name, positional, option name/alias, default, `required` flag, and choices list must survive the migration EXACTLY — the `cli-surface.json` snapshot test is the gate.
- Modules under 200 non-comment LOC; governed dirs max 4 direct files (README.md/`__init__.py` exempt in `src/`), max 3 child dirs; new `src/` dirs need README.md.
- `fetch_url() -> tuple[str, bytes, dict[str, str]]` contract unchanged; retries bounded (3 attempts, backoff) on connect errors and 5xx only; ingest error surfaces (`SystemExit(f"Failed to fetch {url}: ...")`) unchanged.
- Console scripts stay `cr-kit = "cli:main"`, `crk-ledger = "adapters.interfaces.cli.entry:main"` (pinned by `test_console_scripts_stay_stable`).
- Test command form: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest <path> -q` — abbreviated `PYTEST <path>`.
- Commits end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Freeze the CLI surface snapshot

**Files:**
- Create: `deployment/scripts/checks/cli_surface.py` (introspection helper; check `deployment/scripts/checks/` shape first — if at 4 files, nest as `deployment/scripts/checks/cli/surface.py` with README)
- Create: `docs/guides/cli-surface.json` (frozen snapshot; `docs/guides/` has 2 direct files — becomes 3)
- Test: `tests/quality/governance/platform/test_ci_parity.py` — check its LOC headroom; the surface test joins THIS file (platform/ dir is at 4 files, no new file). If it lacks headroom, report BLOCKED with counts.

**Interfaces:**
- Produces: `cli_surface(parser_or_click_cmd) -> dict` returning `{command_name: {"args": [...], "options": {name: {"default": ..., "required": bool, "choices": [...] | None, "is_flag": bool}}}}` for both argparse parsers and click/typer command trees; the committed snapshot file; governance test `test_cli_surface_matches_snapshot`.

- [ ] **Step 1: Write the introspection helper**

```python
"""Introspect CLI surfaces (argparse or click) into a comparable dict."""

from __future__ import annotations

import argparse
from typing import Any


def argparse_surface(parser: argparse.ArgumentParser) -> dict[str, Any]:
    surface: dict[str, Any] = {}
    subactions = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    for sub in subactions:
        for name, subparser in sub.choices.items():
            args: list[str] = []
            options: dict[str, Any] = {}
            for action in subparser._actions:
                if isinstance(action, argparse._HelpAction):
                    continue
                if not action.option_strings:
                    args.append(action.dest)
                    continue
                key = max(action.option_strings, key=len)
                options[key] = {
                    "default": action.default,
                    "required": bool(action.required),
                    "choices": sorted(action.choices) if action.choices else None,
                    "is_flag": isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)),
                }
            surface[name] = {"args": args, "options": dict(sorted(options.items()))}
    return dict(sorted(surface.items()))


def click_surface(root) -> dict[str, Any]:
    import click

    surface: dict[str, Any] = {}
    for name, cmd in root.commands.items():
        args: list[str] = []
        options: dict[str, Any] = {}
        for param in cmd.params:
            if isinstance(param, click.Argument):
                args.append(param.name)
                continue
            key = max(param.opts, key=len)
            options[key] = {
                "default": param.default,
                "required": bool(param.required),
                "choices": sorted(param.type.choices) if isinstance(param.type, click.Choice) else None,
                "is_flag": bool(param.is_flag),
            }
        surface[name] = {"args": args, "options": dict(sorted(options.items()))}
    return dict(sorted(surface.items()))
```

- [ ] **Step 2: Generate and commit the snapshot from the CURRENT argparse parsers**

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -c "
import json
from deployment.scripts.checks.cli_surface import argparse_surface
from adapters.interfaces.cli.parser import build_parser
from cli import build_parser as crkit_parser  # verify the actual builder name in src/cli.py first; adjust import
snapshot = {'crk-ledger': argparse_surface(build_parser()), 'cr-kit': argparse_surface(crkit_parser())}
open('docs/guides/cli-surface.json', 'w').write(json.dumps(snapshot, indent=2, sort_keys=True, default=str) + '\n')
print(sum(len(v) for v in snapshot.values()), 'commands frozen')
"
```

Expected: `33 commands frozen` (25 ledger + 8 cr-kit). Inspect the JSON — every command you know (`init-case`, `ingest-url`, `validate`, `plan`, `resume`, …) must appear with its flags.

- [ ] **Step 3: Add the governance test (in `test_ci_parity.py`)**

```python
def test_cli_surface_matches_snapshot():
    import json

    from deployment.scripts.checks.cli_surface import argparse_surface  # click_surface after migration
    from adapters.interfaces.cli.parser import build_parser

    snapshot = json.loads((KIT_ROOT / "docs" / "guides" / "cli-surface.json").read_text(encoding="utf-8"))
    assert argparse_surface(build_parser()) == snapshot["crk-ledger"]
```

(cr-kit side analogous; after Tasks 3-4 this test switches to `click_surface` — Task 5 owns that edit. The `default=str` in snapshot generation means non-JSON defaults compare via their string form; apply the same normalization when comparing, e.g. run the live surface through `json.loads(json.dumps(surface, default=str))` before asserting.)

Run: `PYTEST tests/quality/governance/platform/test_ci_parity.py -q` — Expected: PASS (frozen == current).

- [ ] **Step 4: Commit**

```bash
git add deployment/scripts/checks/cli_surface.py docs/guides/cli-surface.json tests/quality/governance/platform/test_ci_parity.py
git commit -m "test(cli): freeze CLI surface snapshot before typer migration"
```

---

### Task 2: httpx acquisition swap

**Files:**
- Modify: `src/adapters/io/acquisition/http.py` (full rewrite)
- Modify: `src/adapters/io/acquisition/search.py:1-35` (urllib → httpx)
- Test: `tests/runtime/unit/ops/` is at 4 files — put `test_http_fetch.py` under `tests/runtime/unit/interfaces/` (2 files, io-boundary intent) — verify shape after.

**Interfaces:**
- Produces: `fetch_url(url: str, timeout: int = 25) -> tuple[str, bytes, dict[str, str]]` — same contract; follows redirects; retries connect errors and 5xx responses up to 3 attempts with `0.5 * 2**attempt` backoff; raises `httpx.HTTPError` subclasses on final failure (callers catch broad `Exception`, unchanged). `discover_sources` keeps its exact signature and payload handling.

- [ ] **Step 1: Write the failing tests**

`tests/runtime/unit/interfaces/test_http_fetch.py`:

```python
"""httpx-backed fetch_url: contract, retries, redirects."""

from __future__ import annotations

import httpx
import pytest

from adapters.io.acquisition.http import DEFAULT_USER_AGENT, fetch_url


def _transport(handler):
    return httpx.MockTransport(handler)


def test_fetch_url_contract(monkeypatch):
    def handler(request):
        assert request.headers["User-Agent"] == DEFAULT_USER_AGENT
        return httpx.Response(200, headers={"Content-Type": "text/html"}, content=b"<html>ok</html>")

    monkeypatch.setattr("adapters.io.acquisition.http._transport_for_tests", _transport(handler))
    content_type, body, headers = fetch_url("https://example.org/x")
    assert content_type.startswith("text/html")
    assert body == b"<html>ok</html>"
    assert headers["content-type"].startswith("text/html")


def test_fetch_url_retries_5xx_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(500) if calls["n"] < 3 else httpx.Response(200, content=b"ok")

    monkeypatch.setattr("adapters.io.acquisition.http._transport_for_tests", _transport(handler))
    monkeypatch.setattr("adapters.io.acquisition.http._sleep", lambda s: None)
    _, body, _ = fetch_url("https://example.org/x")
    assert body == b"ok" and calls["n"] == 3


def test_fetch_url_gives_up_after_three_attempts(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503)

    monkeypatch.setattr("adapters.io.acquisition.http._transport_for_tests", _transport(handler))
    monkeypatch.setattr("adapters.io.acquisition.http._sleep", lambda s: None)
    with pytest.raises(httpx.HTTPStatusError):
        fetch_url("https://example.org/x")
    assert calls["n"] == 3


def test_fetch_url_does_not_retry_4xx(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(404)

    monkeypatch.setattr("adapters.io.acquisition.http._transport_for_tests", _transport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        fetch_url("https://example.org/x")
    assert calls["n"] == 1
```

Run: `PYTEST tests/runtime/unit/interfaces/test_http_fetch.py -q` — Expected: FAIL (no `_transport_for_tests`, urllib implementation).

- [ ] **Step 2: Rewrite `http.py`**

```python
"""HTTP acquisition helpers for public-source capture, httpx-backed with bounded retries."""

from __future__ import annotations

import time

import httpx

DEFAULT_USER_AGENT = "truecrime-research-kit/0.1 (+public-interest research; contact: local-user)"
_RETRY_ATTEMPTS = 3
_transport_for_tests: httpx.BaseTransport | None = None


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def fetch_url(url: str, timeout: int = 25) -> tuple[str, bytes, dict[str, str]]:
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    last_exc: Exception | None = None
    with httpx.Client(follow_redirects=True, timeout=timeout, transport=_transport_for_tests) as client:
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                response = client.get(url, headers=headers)
                if response.status_code >= 500 and attempt < _RETRY_ATTEMPTS - 1:
                    _sleep(0.5 * 2**attempt)
                    continue
                response.raise_for_status()
                return response.headers.get("Content-Type", ""), response.content, dict(response.headers)
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt < _RETRY_ATTEMPTS - 1:
                    _sleep(0.5 * 2**attempt)
                    continue
                raise
    assert last_exc is not None  # unreachable; loop either returned or raised
    raise last_exc
```

Note the 5xx-exhaustion path: on the final attempt the `raise_for_status()` raises `HTTPStatusError` — that is what `test_fetch_url_gives_up_after_three_attempts` expects.

- [ ] **Step 3: Swap `search.py` to httpx**

Replace the `urllib` request block in `discover_sources` (keep signature, payload handling, and the lead-only semantics untouched):

```python
    import httpx

    response = httpx.get(
        f"{base}/search",
        params={"q": query, "format": "json", "language": "en"},
        headers={"User-Agent": "truecrime-research-kit/0.1 local-source-discovery"},
        timeout=30,
        follow_redirects=True,
    )
    response.raise_for_status()
    payload = response.json()
```

Move the `import httpx` to module top; delete the now-unused `urllib.request` import (keep `urllib.parse` only if still used elsewhere in the file — check).

- [ ] **Step 4: Run tests**

Run: `PYTEST tests/runtime/unit/interfaces/test_http_fetch.py tests/runtime -q` — Expected: PASS (existing ingest tests exercise `fetch_url` via monkeypatching — if any test monkeypatched `urllib`, update it to the new seam and list it in the report).

- [ ] **Step 5: Commit**

```bash
git add src/adapters/io/acquisition/http.py src/adapters/io/acquisition/search.py tests/runtime/unit/interfaces/test_http_fetch.py
git commit -m "feat(acquisition): swap urllib for httpx with bounded retries"
```

---

### Task 3: Typer migration — crk-ledger

**Files:**
- Create: `src/adapters/interfaces/cli/commands/__init__.py`, `casework.py`, `quality.py`, `planning.py`, `reports.py`, `README.md`
- Create: `src/adapters/interfaces/cli/app.py`
- Modify: `src/adapters/interfaces/cli/entry.py` (drive the typer app)
- Delete: `src/adapters/interfaces/cli/parser.py` (only after the surface test passes)

**Interfaces:**
- Consumes: snapshot + `click_surface` (Task 1); every existing handler (`workspace.init_case`, `web.ingest_url`, `validation.validate`, …) unchanged.
- Produces: `app.py` exposes `app: typer.Typer`; `entry.main(argv=None) -> int` runs it with the same `CasefileError → SystemExit(str(exc))` mapping. Command groups: `casework.py` (init-case, add-source, ingest-url, draft-extraction, ner-suggest, link-names, import-extraction, validate), `quality.py` (dedupe, preserve-source, resolve-identities, audit-contradictions + the four safety commands), `planning.py` (plan-public-records, index-transcript, plan-open-records + remaining planning commands), `reports.py` (timeline/case-outputs/case-charts/clusters/analysis-charts commands). Read `parser.py` and assign every one of the 25 commands to exactly one group; keep each module under 200 non-comment LOC.

- [ ] **Step 1: Establish the wrapper pattern (worked example — `casework.py`, first two commands)**

```python
"""Typer commands: case workspace and intake."""

from __future__ import annotations

import argparse

import click
import typer

from adapters.ops.casework.records import extractions, validation, workspace
from adapters.ops.casework.records.intake import suggestions, web

app = typer.Typer(no_args_is_help=True)

GRADES = click.Choice(["A", "B", "C", "D", "X"])


@app.command("init-case", help="Create a case workspace")
def init_case(
    case_dir: str = typer.Argument(...),
    title: str | None = typer.Option(None, "--title"),
    scope: str | None = typer.Option(None, "--scope"),
    public_interest: str | None = typer.Option(None, "--public-interest"),
) -> None:
    workspace.init_case(argparse.Namespace(case_dir=case_dir, title=title, scope=scope, public_interest=public_interest))


@app.command("add-source", help="Register a source manually")
def add_source(
    case_dir: str = typer.Argument(...),
    title: str = typer.Option(..., "--title"),
    url: str | None = typer.Option(None, "--url"),
    source_type: str = typer.Option("news_article", "--source-type"),
    reliability_grade: str = typer.Option("C", "--reliability-grade", click_type=GRADES),
    author: str | None = typer.Option(None, "--author"),
    publisher: str | None = typer.Option(None, "--publisher"),
    date_published: str | None = typer.Option(None, "--date-published"),
    archive_url: str | None = typer.Option(None, "--archive-url"),
    notes: str = typer.Option("", "--notes"),
    no_public_export: bool = typer.Option(False, "--no-public-export"),
) -> None:
    workspace.add_source(argparse.Namespace(
        case_dir=case_dir, title=title, url=url, source_type=source_type,
        reliability_grade=reliability_grade, author=author, publisher=publisher,
        date_published=date_published, archive_url=archive_url, notes=notes,
        no_public_export=no_public_export,
    ))
```

Transcription rules for the remaining 23 commands (apply mechanically, `parser.py` is the source of truth):
- `p.add_argument("x")` → `x: str = typer.Argument(...)`; `type=int` → `int`.
- `--flag` with `default=None` → `str | None = typer.Option(None, "--flag")`; non-None default → that default; `required=True` → `typer.Option(...)` (ellipsis).
- `action="store_true"` → `bool = typer.Option(False, "--flag")`.
- `choices=[...]` → `click_type=click.Choice([...])`.
- `help=` strings on `add_parser` → the `@app.command(help=...)` verbatim.
- The Namespace passed to the handler must contain EVERY dest the old subparser defined — the surface test catches missing options, and a missing Namespace attribute crashes the handler at runtime; transcribe dest names exactly (dashes→underscores as argparse does).

- [ ] **Step 2: Assemble `app.py` and rewire `entry.py`**

```python
"""crk-ledger typer application."""

from __future__ import annotations

import typer

from adapters.interfaces.cli.commands import casework, planning, quality, reports

app = typer.Typer(help="True Crime / Cult-Origin Research CLI", no_args_is_help=True)
for group in (casework, planning, quality, reports):
    for command in group.app.registered_commands:
        app.registered_commands.append(command)
```

`entry.py`:

```python
"""Ledger CLI executable entry."""

from __future__ import annotations

import click
import typer

from core.casefile import CasefileError

from adapters.interfaces.cli.app import app


def main(argv: list[str] | None = None) -> int:
    command = typer.main.get_command(app)
    try:
        command.main(args=argv, standalone_mode=False)
    except CasefileError as exc:
        raise SystemExit(str(exc)) from exc
    except click.exceptions.Abort as exc:
        raise SystemExit(1) from exc
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
    return 0
```

(`standalone_mode=False` keeps `SystemExit` semantics testable and lets `CasefileError` propagate to the same message the old entry produced.)

- [ ] **Step 3: Flip the surface test to click introspection for crk-ledger**

In the Task 1 test, replace the crk-ledger half:

```python
    import typer.main

    from adapters.interfaces.cli.app import app

    live = click_surface(typer.main.get_command(app))
    assert json.loads(json.dumps(live, default=str)) == snapshot["crk-ledger"]
```

Run: `PYTEST tests/quality/governance/platform/test_ci_parity.py -q`
Expected: PASS — every mismatch it prints is a transcription bug; fix the command module, not the snapshot. THE SNAPSHOT FILE MUST NOT CHANGE IN THIS TASK.

- [ ] **Step 4: Delete `parser.py`, run everything**

```bash
git rm src/adapters/interfaces/cli/parser.py
```

Run: `PYTEST tests/runtime tests/quality/governance -q` and the smoke:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- crk-ledger validate data/examples/synthetic_case
uv run --cache-dir .uv-cache --no-project --with-editable . -- crk-ledger --help | head -30
```

Expected: validation passes; help lists all 25 commands. Update any test importing `build_parser` (grep `from adapters.interfaces.cli.parser` across tests/) to go through `entry.main` or the app — list each in the report.

- [ ] **Step 5: Commit**

```bash
git add -A src/adapters/interfaces/cli tests/
git commit -m "refactor(cli): migrate crk-ledger to typer behind frozen surface"
```

---

### Task 4: Typer migration — cr-kit

**Files:**
- Modify: `src/cli.py` (rewrite parser block as typer wrappers; `main` keeps constructing `CrkSettings()` once and passing values/`_env_override` exactly as today)

**Interfaces:**
- Consumes: Task 1 snapshot; `run_plan_command`, `run_discover_command`, `run_parse_command`, `run_ocr_command`, `run_index_command`, `run_query_command`, `run_remember_command`, `run_resume_command` (all keep their `(args)` signatures); `CrkSettings`/`_env_override` from stage 1.
- Produces: `cli.app: typer.Typer` and `cli.main(argv=None) -> int` (entry point name pinned). The settings object attaches to the Namespace exactly as before (`args.settings = settings`) — construct ONE `CrkSettings()` inside `main()`/a callback, never at import time; the boundary-enforcement grep test from stage 1 still applies.

- [ ] **Step 1: Transcribe the 8 commands** with the same wrapper rules as Task 3 (source of truth: the current `src/cli.py` subparser block). Pattern for the settings bridge — build the Namespace in the wrapper, fetch settings from the typer context:

```python
@app.command("plan", help="Plan and optionally execute the initial case-building workflow.")
def plan(ctx: typer.Context, case_dir: str = typer.Argument(...), ...) -> None:
    args = argparse.Namespace(case_dir=case_dir, ..., settings=ctx.obj)
    run_plan_command(args)


@app.callback()
def _root(ctx: typer.Context) -> None:
    from core.config import CrkSettings

    ctx.obj = CrkSettings()
```

(The callback runs once per invocation — that IS the process-boundary construction.)

- [ ] **Step 2: Flip the cr-kit half of the surface test** to `click_surface(typer.main.get_command(cli_module.app))`, same normalization as Task 3 Step 3. Run it. Expected: PASS with the snapshot unchanged.

- [ ] **Step 3: Full suites + smoke**

Run: `PYTEST tests/runtime tests/quality/governance -q`, then:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- cr-kit plan data/examples/synthetic_case | tail -3
CRK_QDRANT_PORT=7777 uv run --cache-dir .uv-cache --no-project --with-editable . -- python -c "from core.config import CrkSettings; assert CrkSettings().qdrant_port == 7777; print('env ok')"
```

Expected: dry-run plan prints; `env ok`. Update tests that imported the old cr-kit parser builder; list them.

- [ ] **Step 4: Commit**

```bash
git add src/cli.py tests/
git commit -m "refactor(cli): migrate cr-kit to typer behind frozen surface"
```

---

### Task 5: Docs, changelog, verification

**Files:**
- Modify: `CHANGELOG.md` (`## [Unreleased]`), `src/adapters/interfaces/cli/README.md`

- [ ] **Step 1: CHANGELOG**

```markdown
### Changed
- Both CLIs (`crk-ledger`, `cr-kit`) migrated from argparse to typer; every command, flag, default, and choice list is preserved verbatim, enforced by the frozen surface snapshot in `docs/guides/cli-surface.json`.
- URL ingestion and SearXNG discovery now use httpx with redirect handling and bounded retries (3 attempts, exponential backoff) on connect errors and 5xx responses.
```

- [ ] **Step 2: Update the CLI README** (command groups layout, wrapper pattern, the snapshot contract: "changing the CLI surface requires deliberately regenerating `docs/guides/cli-surface.json`").

- [ ] **Step 3: Full verification**

```bash
moon run crk:check && moon run crk:test
uv run --cache-dir .uv-cache --no-project --with-editable '.[governance]' -- python deployment/scripts/checks/fresh_build.py
```

Expected: all green (fresh build proves the packaged wheel still exposes both entry points).

- [ ] **Step 4: Commit, then finish the branch** via superpowers:finishing-a-development-branch. Do not push tags.
