# Bootstrap Environment Prompting And Secure Storage Plan

> **For agentic workers:** This is a documentation and implementation plan, not
> implementation. Execute task-by-task only after the user explicitly asks to
> implement it. Keep unrelated dirty files out of scope.

**Goal:** Extend the CRK bootstrap path so fresh installs can configure the
selected local workflow interactively, write ignored environment files with
restrictive permissions, and generate local SearXNG secret material only when
needed. Preserve current toolchain-only behavior for CI and non-interactive
shells.

**Architecture:** Keep shell and PowerShell wrappers thin. Add one stdlib-only
Python helper under `deployment/scripts/` that owns prompt schema, validation,
dotenv rendering, secure writes, and generated SearXNG local settings. The
wrappers install the toolchain as they do today, then call the helper only when
interactive configuration is requested. Compose continues to work without
generated files, but can mount a generated SearXNG local config through a new
registered `CRK_SEARXNG_SETTINGS_FILE` variable.

**Tech stack:** Python stdlib, Bash, PowerShell, pytest, Moon, Docker Compose
config validation when available.

## Global Constraints

- Do not add required runtime dependencies.
- Do not introduce managed provider/API-key prompts.
- Do not mutate `deployment/searxng/settings.yml`.
- Do not store Codex auth material.
- Do not block non-TTY bootstrap runs.
- Keep `deployment/scripts/` within repository-shape limits. It currently has
  room for one direct helper file; if more files are needed, split into a
  README-bearing child directory and update governance intentionally.
- Update both env registries when adding `CRK_SEARXNG_SETTINGS_FILE`:
  `docs/registry/env_vars.json` and
  `src/crime_research_kit/_runtime/core/lanes/registry_data/env_vars.json`.
- Stage only the files created for this plan. The working tree may already have
  unrelated MKUltra e2e edits.

## Task 0: Branch And Baseline

**Files:** none.

- [ ] Run `git status --short --branch`.
- [ ] Confirm the branch is `dev` or create a focused branch from `dev`.
- [ ] Record existing unrelated dirty paths and avoid staging them.
- [ ] Run the current read-only baseline checks that do not require network:

```bash
moon run crk:check
moon run crk:test-governance
```

Expected: existing repo health is known before bootstrap changes begin. If a
baseline fails due to the current dirty worktree or missing optional deps,
record the exact failure before editing.

## Task 1: Define The Bootstrap Env Helper Contract

**Files:**

- Create: `deployment/scripts/bootstrap_env.py`
- Create: `tests/runtime/unit/deployment/README.md` if the directory is new.
- Create: `tests/runtime/unit/deployment/test_bootstrap_env_schema.py`

**Interfaces:**

- `ConfigWorkflow`: enum-like values `core`, `self-hosted`, `mcp`,
  `live-tests`, `exposed-searxng`.
- `ConfigField`: name, label, default, scope, sensitive flag, validator,
  workflow membership, and optional derived value.
- `schema_for(workflow) -> list[ConfigField]`.
- `derive_values(values) -> dict[str, str]`.
- `validate_values(values, workflow) -> list[str]`.

**Tests:**

- [ ] `core` has no required stored fields.
- [ ] `self-hosted` includes `CRK_MODEL`, `CRK_EMBED_MODEL`,
  `CRK_SEARXNG_HOST_PORT`, and `SEARXNG_BASE_URL`.
- [ ] `SEARXNG_BASE_URL` derives from `CRK_SEARXNG_HOST_PORT`.
- [ ] `CRK_MODEL` accepts `ollama:llama3.1` and rejects `openai:gpt-...`.
- [ ] Port validation rejects empty strings, non-integers, `0`, and `65536`.
- [ ] URL validation requires `http://` or `https://` and normalizes the
  trailing slash.
- [ ] Live-test fields are not part of the default self-hosted workflow.
- [ ] No field is marked sensitive except generated SearXNG secret material.

**Verification:**

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- \
  python -m pytest tests/runtime/unit/deployment/test_bootstrap_env_schema.py -q
```

## Task 2: Dotenv Rendering And Secure File Writes

**Files:**

- Modify: `deployment/scripts/bootstrap_env.py`
- Create: `tests/runtime/unit/deployment/test_bootstrap_env_writer.py`

**Interfaces:**

- `render_dotenv(values) -> str`
- `write_secure(path, content, *, force=False, secret=False) -> WriteResult`
- `refuse_unsafe_target(path) -> None`

**Tests:**

- [ ] Dotenv keys render in stable sorted order.
- [ ] Rendered files end with exactly one newline.
- [ ] Values with spaces or special characters are quoted safely.
- [ ] Unsupported newline values are rejected with a clear error.
- [ ] New POSIX files are mode `0600`.
- [ ] Rewrites preserve restrictive permissions.
- [ ] Existing files are not overwritten unless `force=True`.
- [ ] Symlink destinations are rejected.
- [ ] Atomic replacement does not leave temp files behind after success.
- [ ] Sensitive values are redacted from status output.

**Verification:**

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- \
  python -m pytest tests/runtime/unit/deployment/test_bootstrap_env_writer.py -q
```

## Task 3: Non-interactive CLI Mode

**Files:**

- Modify: `deployment/scripts/bootstrap_env.py`
- Create: `tests/runtime/integration/deployment/README.md` if the directory is
  new.
- Create: `tests/runtime/integration/deployment/test_bootstrap_env_cli.py`

**CLI shape:**

```bash
python deployment/scripts/bootstrap_env.py configure \
  --workflow self-hosted \
  --env-file deployment/.env \
  --non-interactive
```

Supported flags:

- `configure`
- `--workflow core|self-hosted|mcp|live-tests|exposed-searxng`
- `--env-file PATH`
- `--searxng-settings-file PATH`
- `--non-interactive`
- `--force`
- `--dry-run`
- `--set KEY=VALUE` repeatable
- `--print-summary`

**Tests:**

- [ ] `--non-interactive --workflow self-hosted` writes default
  `deployment/.env` values in a temp directory.
- [ ] `--set CRK_SEARXNG_HOST_PORT=19080` derives
  `SEARXNG_BASE_URL=http://127.0.0.1:19080/`.
- [ ] Invalid `--set` values exit non-zero with a clear message.
- [ ] `--dry-run` prints the destination and redacted summary without writing.
- [ ] Existing env file without `--force` exits non-zero and leaves content
  unchanged.
- [ ] `--workflow core` exits zero and writes no env file.

**Verification:**

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- \
  python -m pytest tests/runtime/integration/deployment/test_bootstrap_env_cli.py -q
```

## Task 4: Interactive Prompt Mode

**Files:**

- Modify: `deployment/scripts/bootstrap_env.py`
- Extend: `tests/runtime/integration/deployment/test_bootstrap_env_cli.py`

**Prompt behavior:**

- Prompt with defaults in brackets.
- Empty input accepts the default.
- Invalid input reprompts in a real TTY and exits cleanly in scripted stdin
  after a bounded number of failures.
- Existing files require confirmation unless `--force`.
- The default answer keeps SearXNG localhost-only.

**Tests:**

- [ ] Scripted stdin accepting defaults writes the same content as
  non-interactive defaults.
- [ ] Scripted stdin with custom model/port writes expected values.
- [ ] Invalid port followed by valid port succeeds and records the valid port.
- [ ] Declining overwrite leaves an existing file unchanged.
- [ ] Confirming overwrite replaces an existing file.
- [ ] Prompt output never contains generated secret values.

**Verification:**

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- \
  python -m pytest tests/runtime/integration/deployment/test_bootstrap_env_cli.py -q
```

## Task 5: Generated SearXNG Local Settings

**Files:**

- Modify: `deployment/scripts/bootstrap_env.py`
- Modify: `.gitignore`
- Modify: `.gitleaks.toml`
- Create or extend:
  `tests/runtime/integration/deployment/test_bootstrap_searxng_local.py`

**Behavior:**

- Generate `deployment/searxng/settings.local.yml` only when the user chooses
  non-local SearXNG exposure or explicitly requests `exposed-searxng`.
- Copy the tracked settings shape and replace `server.secret_key` with a random
  generated value.
- Write the local settings file with restrictive permissions.
- Add `CRK_SEARXNG_SETTINGS_FILE=<absolute local settings path>` to
  `deployment/.env`.
- Keep the tracked `deployment/searxng/settings.yml` unchanged.

**Tests:**

- [ ] Local settings file is ignored by Git.
- [ ] Generated `secret_key` is not the placeholder.
- [ ] Two generated files use different secret values.
- [ ] Local settings file is mode `0600` on POSIX.
- [ ] Tracked settings file hash is unchanged.
- [ ] `.gitleaks.toml` allowlists the generated local settings path if needed.
- [ ] Summary output redacts the generated secret.

**Verification:**

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- \
  python -m pytest tests/runtime/integration/deployment/test_bootstrap_searxng_local.py -q
```

## Task 6: Compose And Env Registry Integration

**Files:**

- Modify: `deployment/docker-compose.yml`
- Modify: `docs/registry/env_vars.json`
- Modify:
  `src/crime_research_kit/_runtime/core/lanes/registry_data/env_vars.json`
- Create or extend:
  `tests/runtime/integration/deployment/test_bootstrap_compose.py`

**Behavior:**

- Add `CRK_SEARXNG_SETTINGS_FILE` as a deployment-scoped env var.
- Compose mounts `${CRK_SEARXNG_SETTINGS_FILE:-<tracked settings path>}` to
  `/etc/searxng/settings.yml`.
- `compose.py config` continues to work when no `.env` exists.
- `compose.py config` uses the generated local settings path when it is present
  in `.env`.

**Tests:**

- [ ] Env registry governance passes with `CRK_SEARXNG_SETTINGS_FILE`.
- [ ] `compose.py config` renders the tracked settings mount without `.env`.
- [ ] `compose.py config` renders the local settings mount with generated
  `.env`.
- [ ] `CRK_REPO_ROOT` absolute default from `compose.py` still works.
- [ ] No managed provider env vars are introduced.

**Verification:**

```bash
moon run crk:test-governance
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- \
  python -m pytest tests/runtime/integration/deployment/test_bootstrap_compose.py -q
```

## Task 7: Bootstrap Shell Wrapper

**Files:**

- Modify: `deployment/scripts/bootstrap.sh`
- Create or extend:
  `tests/runtime/integration/deployment/test_bootstrap_wrappers.py`

**Behavior:**

- Preserve the existing install sequence.
- Add wrapper flags:
  - `--toolchain-only`
  - `--configure`
  - `--workflow <name>`
  - `--non-interactive`
  - `--force`
- In a TTY, offer the self-hosted configuration prompt after toolchain install.
- In non-TTY mode, do not prompt unless explicit non-interactive configuration
  flags are supplied.
- Support test stubs so wrapper tests do not invoke network installers.

**Tests:**

- [ ] With stubbed `proto` and `uv`, `--toolchain-only` runs old behavior and
  does not call the helper.
- [ ] With `--configure --non-interactive --workflow self-hosted`, wrapper
  calls `bootstrap_env.py configure`.
- [ ] Non-TTY run without `--configure` exits without prompt.
- [ ] Missing helper failure propagates as non-zero.
- [ ] PATH updates remain intact after installing proto/uv.

**Verification:**

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- \
  python -m pytest tests/runtime/integration/deployment/test_bootstrap_wrappers.py -q
```

## Task 8: PowerShell Wrapper

**Files:**

- Modify: `deployment/scripts/bootstrap.ps1`
- Extend: `tests/runtime/integration/deployment/test_bootstrap_wrappers.py`

**Behavior:**

- Mirror Bash flags with PowerShell parameters:
  - `-ToolchainOnly`
  - `-Configure`
  - `-Workflow`
  - `-NonInteractive`
  - `-Force`
- Preserve the existing install sequence.
- Use the same Python helper for configuration.
- Skip wrapper tests when `pwsh` is unavailable.

**Tests:**

- [ ] `pwsh` wrapper `-ToolchainOnly` does not call the helper.
- [ ] `-Configure -NonInteractive -Workflow self-hosted` calls helper with
  equivalent flags.
- [ ] Non-interactive default run does not prompt.
- [ ] Windows path quoting is preserved for env-file arguments.

**Verification:**

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- \
  python -m pytest tests/runtime/integration/deployment/test_bootstrap_wrappers.py -q
```

## Task 9: Docs And Runbook Updates

**Files:**

- Modify: `deployment/README.md`
- Modify: `deployment/scripts/README.md`
- Modify: `docs/guides/runbooks/setup/install/core.md`
- Modify: `docs/guides/runbooks/setup/requirements.md`
- Modify: `docs/guides/runbooks/setup/self-hosted-deployment.md`
- Optional: add a focused setup page if existing docs become too long.

**Documentation requirements:**

- Explain toolchain-only versus configured bootstrap.
- Document where generated env files live and that they are ignored.
- Document that current bootstrap has no API-key prompts.
- Document SearXNG local-only default and local settings generation for
  exposure.
- Replace copy-only first-run examples with the new helper path while retaining
  manual fallback.
- Keep README-level docs concise; detailed flow belongs in setup runbooks.

**Tests:**

- [ ] Docs mention `deployment/.env` and generated local settings storage.
- [ ] Docs do not tell users to commit generated env files.
- [ ] Docs preserve the local-first/no-managed-provider boundary.
- [ ] `moon run crk:test-governance` docs-link checks pass.

## Task 10: Broad Verification Gate

Run the focused and broad checks in this order:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- \
  python -m pytest tests/runtime/unit/deployment -q

uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- \
  python -m pytest tests/runtime/integration/deployment -q

moon run crk:check
moon run crk:test-governance
moon run crk:test-smoke
```

If Docker is available:

```bash
moon run crk:docker-config
```

If the local stack is intentionally running:

```bash
moon run crk:docker-up
moon run crk:docker-smoke
```

Expected result:

- Unit and integration tests pass without network.
- Governance passes, including env registry and secret floor.
- Smoke tests pass or skip only optional/live paths.
- Docker config renders with and without generated env files.
- Live stack smoke is optional but should pass when the operator chooses to run
  it.

## Task 11: Commit Boundary

Recommended commit series:

1. `feat(deployment): add bootstrap env configuration helper`
2. `test(deployment): cover secure env writes and prompt flows`
3. `feat(deployment): support generated local SearXNG settings`
4. `docs(setup): document bootstrap environment configuration`

Before each commit:

```bash
git status --short
git diff --check
```

Stage explicit paths only. Do not stage unrelated MKUltra e2e or local-stack
work unless that becomes part of a separate requested task.
