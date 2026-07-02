# True Crime / Cult Research Skill API Spec

Status: draft v0.1  
Applies to: `.agents/skills/truecrime-cult-research`  
Primary implementation: `crk-ledger`

This page is the stable entry point for the machine-facing CLI and JSONL
contract. The detailed contract is split into governed shards under
`docs/guides/integrations/skill-api/` so each reference file stays small.

## Reference Shards

| Topic | File |
|---|---|
| Overview, safety, and case data layout | [Overview](integrations/skill-api/contract/overview.md) |
| Record conventions and source support | [Record conventions](integrations/skill-api/contract/record-conventions.md) |
| Request/response envelope and core operations | [Core operations](integrations/skill-api/operations/core.md) |
| Review and planning operations | [Review operations](integrations/skill-api/operations/review-planning.md) |
| Export operations | [Export artifacts](integrations/skill-api/exports/artifacts.md) |
| Future HTTP mapping and versioning | [HTTP and versioning](integrations/skill-api/exports/http-versioning.md) |

## Canonical Vocabulary

Lane and template vocabulary is canonical in `docs/registry/`. Generated
human reference tables live in
`.agents/skills/truecrime-cult-research/references/lane_registry.md` and
`.agents/skills/public-records-router/references/routing_matrix.md`; public
docs should point to those sources instead of duplicating lane tables.

## Compatibility

The path `docs/guides/skill-api-spec.md` remains the canonical link target for
README files, architecture docs, and external references. Add new operation
details to the shards above, then keep this index current.
