# Agent Skills

Repo-local skills live under `.agents/skills/`. `truecrime-cult-research` is
the case-ledger and safety baseline skill. Agents discover repo skills there.

## Invoking the core skill

These prompts work for Codex and similar skill-aware agents.

```text
Use the $truecrime-cult-research skill. Build a case file for [topic]. Find public news sources, eyewitness accounts, and official records. Save sources, extract entities/events/claims, flag contradictions, and export Manim-ready CSVs.
```

Or ask:

```text
Use the truecrime-cult-research skill to create a data-first source map for the origins of [group/case]. Start with public news coverage and eyewitness accounts, but do not publish private-person details or infer guilt.
```

## Adjacent skill routing

Use `truecrime-cult-research` as the case ledger and safety baseline. Route
domain-heavy packets to adjacent skills only when their lane applies.

Adjacent skills write source-traceable entities, claims, events, relationships,
artifacts, and notes back into the same TRCR case structure.

## Registry is canonical

Canonical lane/template metadata lives in [`docs/registry/`](../../registry/).
The reference tables in
`.agents/skills/truecrime-cult-research/references/lane_registry.md` and
`.agents/skills/public-records-router/references/routing_matrix.md` are
generated from it, and governance tests catch drift between them. Update the
registry shards first, never the generated tables.

## Safety defaults for agents

All skill work inherits the TRCR safety contract:

- AI-generated summaries are never evidence; extraction packets are staged
  under `staging/extractions/` for human review before import.
- Never infer guilt, membership, motive, or participation from proximity or
  co-mention; automation-created co-mention records must be
  `status: unverified`, low confidence, `public_export: false`.
- Only apply labels like suspect/perpetrator/cult member when a cited source
  uses that wording; prefer neutral roles.
- Preserve uncertainty in `status`/`confidence`/`notes` instead of smoothing
  it away.

## Hosts without repo-local skills

Hosts that cannot discover `.agents/skills/` (Claude Desktop and other MCP
clients) can drive the same ledger through the [MCP server](mcp-server.md),
which exposes the case-builder ops core as tools, prompts, and resources.

## Related

- [Skill API Spec](../skill-api-spec.md)
- [MCP Server](mcp-server.md)
- [Case Workflow](../runbooks/cases/case-workflow.md)
