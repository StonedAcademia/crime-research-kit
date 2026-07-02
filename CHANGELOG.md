# Changelog

All notable changes to this project are documented here.

The format follows Keep a Changelog, and this project uses semantic versioning.

## [Unreleased]

### Changed

- Retired the legacy wrapper command surface in favor of direct `moon run crk:<task>` usage across CI, governance checks, and operator docs.

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
