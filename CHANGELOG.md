# Changelog

All notable changes to this project are documented here.

The format follows Keep a Changelog, and this project uses semantic versioning.

## [Unreleased]

## [0.13.0] - 2026-07-03

### Added

- Added the initial public `crime_research_kit.sdk` namespace with a lightweight
  `CrkContext`, `SafetyTier`, `OperationSpec`, and empty operation catalog.
- Added public SDK `OperationResult`, `OperationWarning`, `CrkError`, stable
  error codes, and dependency/safety/privacy/input error subclasses.
- Added `TransportMode` and expanded `CrkContext` so SDK callers can carry
  roots, resolved settings, privacy defaults, and runtime transport selection.
- Added top-level `CrkClient` and case-scoped `CaseClient` handles for SDK
  callers.
- Added SDK case and record read wrappers for case listing, public-safe case
  info, record listing, and source-text reads.
- Added SDK source wrappers for source registration, URL ingestion,
  preservation, discovery, parsing, and OCR with actionable optional failures.
- Added a metadata-only `OperationSpec` catalog with safety tiers,
  side-effect descriptions, request/result model names, and CLI/MCP/Skill API
  mappings for the initial SDK operation set.
- Added Skill API operation docs drift checks against the SDK catalog and
  `OperationResult` envelope.
- Added SDK catalog parity tests that ensure current CLI commands and MCP tools
  are represented by catalog entries.
- Added SDK import tests that verify `crime_research_kit.sdk` does not import
  or export legacy runtime roots as public API.
- Added package-discovery governance so built wheels include the public
  `crime_research_kit*` namespace.
- Added fresh-build import coverage for `crime_research_kit.sdk`.
- SDK target-shape planning package covering the public `crime_research_kit.sdk`
  namespace, extraction phases, and first-wave kanban orchestration.
- Typed pydantic models for all twelve ledger record types
  (`core.models.records`), drift-tested against the canonical schemas.
- Record schemas ship as package data, so installed packages validate without a
  repo checkout.
- Per-case vocabulary overrides:
  `data/cases/<slug>/analysis_vocabulary.json` extends or prepends the default
  packs, with a worked example in `data/examples/synthetic_case/`.
- Governance tests banning case-specific vocabulary from `src/` and validating
  the new registry shards.
- Frozen CLI-surface governance for both console scripts.

### Changed

- Adopted a pinned required-dependency set (`jsonschema`, `pydantic`, `pydantic-settings`, `httpx`, `typer`, `jinja2`); the core package is no longer stdlib-only.
- `crk-ledger validate` now enforces the full JSON Schemas (enums, types, nested shapes) with line-addressed errors, replacing required-field-only checks.
- Environment configuration is resolved once at CLI/MCP startup via `CrkSettings`; all `CRK_*` variable names and defaults are unchanged.
- Setting an env var to an empty string is now a validation error for integer settings (e.g. `CRK_QDRANT_PORT=""` fails at startup) instead of silently falling back to the default.
- Analysis relationship/family/bridge classification is now driven by vocabulary packs from `docs/registry/analysis/`; records matching no pack or structural rule surface as `unclassified` instead of silently defaulting to `personnel_bridge`.
- Status/grade score tables and layer ordering moved from code constants to the `analysis/scoring.json` and `analysis/vocabulary.json` registry shards.
- Both CLIs (`crk-ledger`, `cr-kit`) migrated from argparse to Typer while preserving command names, positional arguments, flags, defaults, aliases, and choices through `docs/guides/cli-surface.json`.
- URL ingestion and SearXNG discovery now use httpx with redirect handling and bounded retries on connect errors and 5xx responses.
- Analysis, case-chart, and cluster reports now render through typed pydantic models and Jinja2 templates with committed Tailwind/TS assets; output is byte-different but content-equivalent (element/label parity gated against the synthetic case) and remains fully offline-viewable.

### Security

- Preserved the public SDK import boundary so importing `crime_research_kit.sdk`
  does not load CLI, MCP, graph, or ledger runtime modules.

### Fixed

- Included `crime_research_kit*` in setuptools package discovery so the public
  SDK namespace is present in built distributions.

### Removed
- Legacy f-string HTML/SVG renderers (`pages/interactions.py`, string-building `render_*_svg` functions) -- replaced by `core.models.reports` figures and the `templates_data/` template layer.

## [0.12.0] - 2026-07-02

### Added

- Added the packaged `crk-ledger` console script for canonical ledger operations.
- Added `adapters.interfaces.cli` with package-module execution through `python -m adapters.interfaces.cli`.
- Added source-backed case workspace, extraction, intake, name-linking, planning, and validation modules under `src/adapters/ops/casework/records`.
- Added public-export, preservation, identity, contradiction, dedupe, privacy, readiness, and source-independence operations under `src/adapters/ops/evidence/quality`.
- Added case output, timeline, case-chart, people-cluster, and extended analysis export modules under `src/adapters/ops/evidence/reports`.
- Added modular SVG, page, command-context, builder, and output writer components for the extended analysis chart package.

### Changed

- Replaced the legacy `.agents/skills/truecrime-cult-research/scripts/tcr.py` script with the packaged `crk-ledger` CLI.
- Updated `CrkRunner`, MCP tools, pipeline tests, Moon sample tasks, deployment smoke checks, runbooks, skill docs, and course docs to invoke the packaged ledger CLI.
- Renamed evidence helper modules from the vague `evidence/shared` package to `evidence/ledger`.
- Split the former monolithic ledger script into bounded `src` modules with per-directory README ownership notes.
- Centered the square README artwork and kept the release docs aligned with the packaged CLI surface.

### Security

- Moved URL fetching into `adapters.io.acquisition` so network-capable code stays inside the governed acquisition boundary.
- Preserved public-output, privacy-redaction, source-independence, contradiction, and narrative-readiness gates as package modules with focused runtime coverage.
- Added governance coverage that prevents frontends from shelling out to repo-local agent script paths.

### Fixed

- Exempted `README.md` and `__init__.py` under `src` from repository-shape file-count budgets while keeping size checks active.
- Removed stale `tcr.py` command references outside historical `docs/superpowers` materials.
- Fixed path-policy drift by replacing the vague `evidence/shared` package name.
- Updated release packaging expectations for the new `crk-ledger` console script.

## [0.11.1] - 2026-07-02

### Changed

- Changed the project license from MIT to AGPL-3.0-only.
- Retired the legacy wrapper command surface in favor of direct `moon run crk:<task>` usage across CI, governance checks, and operator docs.
- Bumped release metadata for a patch release after the `v0.11.0` release gate exposed stale package import smoke checks.

### Fixed

- Fixed the fresh-build wheel import smoke to import the current `cli`, `core`, `pipeline`, and MCP adapter modules instead of removed `case_builder` package paths.
- Updated the deployment smoke script to use the current `python -m cli` and `adapters.interfaces.mcp.server` entry points.
- Added governance coverage so stale `case_builder` package paths cannot return to the release build and deployment smoke checks.
- Fixed audit-lane drift from `lychee` flag changes and sparse `setuptools` license metadata.

## [0.11.0] - 2026-07-02

### Added

- Packaged CRK case-builder application with the `cr-kit` CLI, source-ledger operations, extraction staging, review/export helpers, and sample case validation.
- LangGraph-style case-building pipeline with capture, parse, draft, review-gate, import, index, audit, export, checkpoint, and resume support.
- Local-first LLM helpers for lane suggestions, extraction packet filling, readiness briefs, provider selection, and explicit egress audit logging.
- MCP server with rooted case resolution, read/query tools, staged-write tools, gated-write tools, resources, and workflow prompts.
- Canonical lane registry with runtime loading, sharded registry data, generated lane references, extraction templates, and skill-routing integration.
- True-crime/cult research skill workflows for public records, criminal research, missing persons, geography, courts, media transcripts, identity resolution, privacy, source preservation, and narrative readiness.
- Self-hosted local deployment stack for Ollama, SearXNG, Qdrant, OCR/document tooling, retrieval, memory, Docker Compose, bootstrap scripts, and container smoke checks.
- UFB bundle exporter, public artifact export wording, and operator runbooks for setup, case workflows, output readiness, and deployment operations.
- Governance program with repository-shape checks, import/network boundaries, env-var registry, local-provider policy, secret scanning, fixture provenance checks, data-safety gates, docs drift checks, packaging policy, and license/SBOM tooling.
- GitHub Actions, Moon/proto task targets, branch gates, governance install path, reproducible release builds, per-extra SBOM generation, and release-readiness validation.

### Changed

- Renamed the public project label from TRCR to CRK across docs, moon tasks, Docker/Compose services, environment variables, generated exports, branch gates, tests, and runtime messages.
- Hoisted the case-builder app into the `src/` namespace with adapter, core, and pipeline groupings while preserving CLI and MCP entry points.
- Reorganized tests into `tests/runtime` and `tests/quality`, with governance checks grouped by docs, platform, policy, smoke, and runtime concerns.
- Restructured public documentation into audience-routed README sections, guides, runbooks, integration docs, API references, schemas, registry docs, and implementation plans.
- Moved lane routing and template behavior from hardcoded choices to the canonical registry and generated references.
- Split large deployment, UFB exporter, integration, and governance test modules into smaller ownership areas.
- Organized repository governance and deployment layout, ignored nested worktrees, and removed generated egg-info metadata from tracking.
- Added branch hygiene guidance for focused feature, governance, canary, hotfix, and mainline release workflows.
- Kept Codex and Claude Code as agent hosts rather than managed CRK runtime model providers.

### Security

- Added local-only runtime provider policy with managed-SaaS provider denial for CRK model configuration.
- Added canonical environment variable registry and checks for approved prefixes and deployment/runtime/CI scopes.
- Added gitleaks-based secret scanning, stdlib secret-pattern floors, and generated-cache exclusions for release audit noise.
- Added import-boundary, lazy optional dependency, and network-confinement governance checks.
- Added public-output safety gates for privacy review, guilt-label linting, weak-corroboration checks, source-span requirements, and unsafe fixture coverage.
- Added fixture schema validation, claim provenance checks, release SBOM output, dependency audit, and license-policy gates.

### Fixed

- Repaired README banner clipping, grammar, runbook routing, internal links, Markdown anchors, and docs discovered by governance drift checks.
- Fixed package-data/build gaps so registry data, lane shards, templates, and packaged resources are present in built artifacts.
- Tuned repository-shape governance after docs/deployment layout changes and added coverage for public command runbooks.
- Updated core validation and public README language for the hoisted `src/` app boundary.
- Excluded generated caches from secret audit to keep release scans focused on tracked source and fixtures.
