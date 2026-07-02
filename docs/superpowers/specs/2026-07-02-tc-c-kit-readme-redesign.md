# README Redesign and Guide Extraction — Design

Date: 2026-07-02
Status: approved (audience segmentation confirmed: Researcher / Operator / Developer)

## Goal

Turn `README.md` into an audience-routed landing page with visuals, and move
guide-type content (architecture, integration, runbook material) into
`docs/guides/`. Create the missing guide artifacts the README currently
substitutes for.

## Audiences

1. **Researcher** — builds cases with the `tcr.py` CLI and repo skills
   (quick start, case workflow, exports, public-output readiness).
2. **Operator** — runs the self-hosted stack (install, docker deployment).
3. **Developer / agent integrator** — MCP server, case-builder app,
   skill API spec, Codex/Claude skill invocation.

## Content moves

| README section | Destination |
| --- | --- |
| Key conventions + Key principle | `docs/guides/architecture/case-ledger.md` (new) |
| How to invoke the skill in Codex + Adjacent skill routing | `docs/guides/integrations/agent-skills.md` (new) |
| Document Structure table | merged into `docs/README.md` |
| App And Integration References table | folded into audience routing table |
| Quick start | stays, trimmed to ~3 commands + case-workflow runbook link |
| (new) | `docs/guides/architecture/system-overview.md` — full architecture with Mermaid diagrams |

## New README shape (~140 non-blank lines)

Banner → pitch + safety statement → evidence-chain Mermaid diagram →
"Choose your path" audience table → trimmed quick start → "What you can
build" table → compact architecture Mermaid + system-overview link →
public-interest boundaries → docs map pointer.

## Constraints

- README and every new guide ≤ 200 non-blank lines
  (`tests/governance/test_repository_shape.py`).
- `docs/guides/` may gain files but no new child directories (at 3-dir cap).
- Safety framing stays prominent in the README.
- Baseline governance failures (19 shape offenders, 8 oversized files,
  including `skill-api-spec.md`, `case-workflow.md`, `install.md`) are
  pre-existing and out of scope; this change must add no new offenders.

## Execution

Parallel independent design passes (deep-reasoner + Codex) synthesized by the
orchestrator; fast-worker performs mechanical content extraction; orchestrator
writes the final README, `system-overview.md` polish, and diagrams; verify with
`pytest -m governance` (no new offenders), `make check`, and a link sweep.
