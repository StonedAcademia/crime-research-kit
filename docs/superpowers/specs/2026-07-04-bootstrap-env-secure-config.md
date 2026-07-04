# Secure Bootstrap Environment Configuration

**Date:** 2026-07-04
**Status:** Draft design
**Scope:** `deployment/scripts/bootstrap.sh`, `deployment/scripts/bootstrap.ps1`,
the local Docker deployment environment, SearXNG local secret handling, MCP
root overrides, and opt-in live-test environment profiles.

## Problem

The bootstrap scripts currently install the minimum toolchain only. They install
or expose `proto`, run `proto use`, ensure `uv` exists, and then point the
operator at `moon run crk:check`. They do not ask whether the operator wants to
configure the self-hosted stack, they do not create `deployment/.env`, and they
do not help with the SearXNG `secret_key` boundary when a user chooses anything
other than the default localhost-only posture.

The runtime configuration surface is documented and mostly defaulted:

- `CrkSettings` reads self-hosted runtime values such as `CRK_MODEL`,
  `CRK_SEARXNG_URL`, `CRK_QDRANT_URL`, `CRK_QDRANT_PORT`, and
  `CRK_EMBED_MODEL`.
- MCP reads `CRK_CASES_ROOT` and `CRK_SKILL_ROOT`, both with repo-local
  defaults.
- Docker Compose reads a small `deployment/.env` profile when present.
- Live MKULTRA and local-stack tests read opt-in test flags such as
  `CRK_LIVE_MKULTRA`, `CRK_LIVE_CODEX`, and `CRK_CODEX_BIN`.

The repo is also intentionally local-first: no managed model-provider API keys,
hosted vector-store tokens, or tracing secrets are part of the current
configuration contract. The secure-bootstrap work must preserve that posture.

## Goals

- Prompt only for information required by the selected workflow, not for every
  registered environment variable.
- Keep the default bootstrap path compatible with unattended shells and CI.
- Store local configuration in ignored files with restrictive permissions.
- Keep non-secret deployment choices separate from secret-bearing local service
  config.
- Generate SearXNG local secret material when the user chooses non-local
  exposure, without mutating the tracked `deployment/searxng/settings.yml`.
- Make the prompt model testable without executing network installers.
- Add broad automated coverage across model selection, file permissions,
  non-interactive behavior, wrapper scripts, docs, governance, and compose
  integration.

## Non-goals

- Adding external SaaS provider configuration or API-key prompts.
- Replacing `CrkSettings` or changing the existing runtime defaults.
- Making the bootstrap script responsible for starting Docker services.
- Persisting Codex authentication material. Codex remains a host CLI/service
  concern, not a CRK runtime secret.
- Moving generated case data or source captures out of the ignored
  `data/cases/` workspace model.

## Configuration Workflows

The prompt surface is selected by workflow. The bootstrap wrappers should offer
these workflows in interactive terminals and expose equivalent flags for
automation.

| Workflow | Default prompt? | Stored file | Purpose |
| --- | --- | --- | --- |
| `core` | No | none | Toolchain-only install, current behavior. |
| `self-hosted` | Yes in a TTY | `deployment/.env` | Local Docker stack choices. |
| `mcp` | Optional advanced | `deployment/.env.mcp` or operator shell profile | Non-default MCP case/skill roots. |
| `live-tests` | Optional advanced | `deployment/.env.live-tests` | Opt-in live test flags and local service URLs. |
| `exposed-searxng` | Only after explicit exposure choice | `deployment/searxng/settings.local.yml` plus `deployment/.env` pointer | Local SearXNG secret key for non-local exposure. |

Default interactive behavior:

1. Install the toolchain exactly as today.
2. If stdin/stdout are TTYs, ask whether to configure the local self-hosted
   stack now.
3. If the user accepts, prompt for self-hosted values with documented defaults.
4. Ask whether SearXNG will remain localhost-only. The default is localhost-only.
5. Ask whether to configure MCP roots or live-test flags only if the user opts
   into advanced setup.

Default non-interactive behavior:

- Do not prompt.
- Do not write environment files unless an explicit `--configure` or
  `--non-interactive --workflow ...` path is provided.
- Print the next command and the path to the configuration command.

## Environment Classes

### Self-hosted Deployment Values

These are non-secret local deployment settings and belong in `deployment/.env`
with mode `0600` on POSIX systems and current-user-only ACLs where practical on
Windows:

| Variable | Prompt label | Default | Validation |
| --- | --- | --- | --- |
| `CRK_MODEL` | Ollama model spec | `ollama:llama3.1` | Must be `ollama:<model>` for this local stack. |
| `CRK_EMBED_MODEL` | Embedding model | `BAAI/bge-small-en-v1.5` | Non-empty string. |
| `CRK_SEARXNG_HOST_PORT` | SearXNG host port | `18080` | Integer, 1-65535. |
| `SEARXNG_BASE_URL` | SearXNG base URL | Derived from host port | Absolute `http://` or `https://` URL ending in `/`. |

`SEARXNG_BASE_URL` should derive from `CRK_SEARXNG_HOST_PORT` unless the user
overrides it. The prompt should explain that changing the port and base URL
together keeps Compose and SearXNG aligned.

### Runtime Values With Existing Defaults

These should not be prompted in the base self-hosted flow because Compose and
runtime code already set safe defaults:

- `CRK_CASES_ROOT`
- `CRK_SKILL_ROOT`
- `CRK_SEARXNG_URL`
- `CRK_QDRANT_URL`
- `CRK_QDRANT_HOST`
- `CRK_QDRANT_PORT`
- `CRK_MEM0_LLM_PROVIDER`
- `CRK_MEM0_LLM_MODEL`
- `CRK_EMBEDDER_PROVIDER`
- `OLLAMA_HOST`
- `HF_HOME`
- `TRANSFORMERS_CACHE`

They remain documented in the env registry and are available for advanced
manual override.

### CI And Release Values

These are not bootstrap prompts:

- `CRK_HOOK_BRANCH`
- `CRK_RELEASE_TAG`
- `SOURCE_DATE_EPOCH`

They remain CI/release controls.

### Live Test Values

These are opt-in test gates, not application requirements:

| Variable | Default | Storage |
| --- | --- | --- |
| `CRK_LIVE_MKULTRA` | unset | Optional `deployment/.env.live-tests` |
| `CRK_LIVE_CODEX` | unset | Optional `deployment/.env.live-tests` |
| `CRK_CODEX_BIN` | `codex` | Optional `deployment/.env.live-tests` |
| `CRK_SEARXNG_URL` | `http://127.0.0.1:<port>` | Optional `deployment/.env.live-tests` |
| `CRK_QDRANT_URL` | `http://127.0.0.1:6333` | Optional `deployment/.env.live-tests` |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Optional `deployment/.env.live-tests` |

The helper may write a sourceable live-test profile, but the normal bootstrap
path must not silently enable live tests.

## Storage Contract

### Files

| Path | Tracked? | Contents | Permission target |
| --- | --- | --- | --- |
| `deployment/.env` | ignored | Non-secret local Compose settings | `0600` POSIX, current user on Windows |
| `deployment/.env.mcp` | ignored | Optional MCP root overrides | `0600` POSIX, current user on Windows |
| `deployment/.env.live-tests` | ignored | Optional live-test opt-in flags | `0600` POSIX, current user on Windows |
| `deployment/searxng/settings.local.yml` | ignored after implementation | Generated SearXNG local config with random `secret_key` | `0600` POSIX, current user on Windows |

### Write Rules

- Use atomic writes: create a temporary file in the destination directory, set
  restrictive permissions before exposing content, then replace the destination.
- Refuse to overwrite a symlink target for any secret-bearing or env file path.
- Do not print secret values to stdout/stderr.
- Preserve existing user files unless `--force`, an interactive confirmation,
  or a targeted `--set key=value` is used.
- Produce stable key ordering to keep diffs readable.
- Quote `.env` values only when needed and escape newlines or unsupported
  characters rather than writing malformed dotenv content.

### Secret Handling

Current CRK bootstrap has no required API keys. The only secret-like local value
in scope is SearXNG `server.secret_key`, and it should be generated by the
helper with at least 32 random bytes encoded as URL-safe text. If future
provider tokens are added, they must not be stored in `deployment/.env` by
default; the design should move to an OS keychain or an explicitly ignored
secret file with redacted status output.

## Compose Integration

The tracked Compose file should continue to work with no generated files. When
`deployment/.env` exists, Compose should load it through the existing
`compose.py` wrapper.

To support generated SearXNG config without mutating tracked YAML, add a
registered deployment variable:

| Variable | Purpose | Default |
| --- | --- | --- |
| `CRK_SEARXNG_SETTINGS_FILE` | Host path mounted to `/etc/searxng/settings.yml` | tracked `deployment/searxng/settings.yml` |

The helper writes `CRK_SEARXNG_SETTINGS_FILE=<absolute path to settings.local.yml>`
only when a local settings file is generated. The Compose volume should use this
value as the source path with the tracked file as the fallback.

## User Experience

Example interactive flow:

```text
Toolchain ready.

Configure local CRK environment now? [Y/n]
Workflow [self-hosted]:
Ollama model spec [ollama:llama3.1]:
Embedding model [BAAI/bge-small-en-v1.5]:
SearXNG host port [18080]:
SearXNG base URL [http://127.0.0.1:18080/]:
Keep SearXNG bound to localhost only? [Y/n]:

Wrote deployment/.env with restricted permissions.
Continue:
  moon run crk:docker-build
  moon run crk:docker-up
```

If the user chooses non-local SearXNG exposure, the helper should warn that
public exposure is not the default posture, generate `settings.local.yml`, set
`CRK_SEARXNG_SETTINGS_FILE`, and point the user at `moon run crk:docker-config`
before startup.

## Acceptance Criteria

- `./deployment/scripts/bootstrap.sh` and
  `.\deployment\scripts\bootstrap.ps1` keep the existing toolchain behavior.
- TTY runs offer self-hosted config prompts after toolchain install.
- Non-TTY runs never block on prompts.
- `deployment/.env` is generated with defaults when the user accepts the
  self-hosted flow.
- Existing `deployment/.env` is not overwritten without confirmation or force.
- Generated env files and SearXNG local settings are ignored by Git and written
  with restrictive permissions.
- The tracked SearXNG settings file remains unchanged.
- `CRK_SEARXNG_SETTINGS_FILE` is registered and covered by env governance.
- Live-test flags remain opt-in and are not enabled by the normal bootstrap.
- No managed provider/API-key prompt is introduced.

## Test Matrix

| Area | Test location | What to assert |
| --- | --- | --- |
| Prompt schema | `tests/runtime/unit/deployment/test_bootstrap_env_schema.py` | Workflow-to-variable mapping, defaults, labels, sensitivity flags, derived `SEARXNG_BASE_URL`. |
| Validation | unit | Invalid ports, malformed URLs, non-`ollama:` model specs, empty required values. |
| Dotenv rendering | unit | Stable ordering, escaping, final newline, no malformed values. |
| Secure writes | unit | POSIX `0600`, atomic replacement, parent dir handling, symlink refusal. |
| Existing file safety | unit/integration | No overwrite by default, overwrite with `--force`, interactive confirmation path. |
| SearXNG local config | unit/integration | Random secret generated, tracked settings untouched, local file ignored, env pointer written. |
| Non-interactive CLI | integration | `--non-interactive --workflow self-hosted` writes defaults and exits 0. |
| Interactive CLI | integration | stdin answers produce expected env files; invalid answer reprompt or controlled failure. |
| Bash wrapper | integration | Stub `proto`, `uv`, and network installers; TTY path invokes config helper; non-TTY does not prompt. |
| PowerShell wrapper | integration, skip without `pwsh` | Same wrapper behavior and path handling on PowerShell. |
| Compose config | integration | Generated `.env` is picked up by `compose.py config`; local SearXNG settings path is mounted. |
| Env registry governance | governance | New env vars are registered, mirrored into runtime registry data, and pass prefix policy. |
| Secret floor | governance | No tracked high-entropy secret is committed; generated ignored secret path is gitleaks-allowlisted if required. |
| Docs links | governance | Setup docs and runbooks link to the new bootstrap configuration path. |
| End-to-end dry run | e2e/smoke | Temp repo copy runs bootstrap config helper, then `moon run crk:docker-config` or direct `compose.py config` succeeds without starting services. |

## Risks And Open Questions

- PowerShell ACL handling can be platform-specific. The test should assert the
  best available current-user restriction and skip Windows-only ACL details when
  `pwsh` is unavailable.
- Docker Compose interpolation for a fallback settings file should be tested
  with `docker compose config` before implementation is considered done.
- `deployment/scripts/` currently has room for one more direct file under the
  repository-shape policy. Adding more helper modules may require a deliberate
  split with a README-bearing child directory.
- If the team later decides to support external providers, this spec should be
  revised before any API-key prompt is added.
