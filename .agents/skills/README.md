# CRK Agent Skills

This directory is intentionally flat. Each direct child directory that contains
`SKILL.md` is a loadable skill. Do not move skills into category subdirectories;
that makes discovery less predictable for skill-aware agents.

## Source Of Truth

| Surface | Purpose |
| --- | --- |
| `docs/registry/` | Canonical lane, template, trigger, and public-record planning metadata. |
| `.agents/skills/catalog.json` | Human and test-readable grouping for the flat skill tree. |
| `.agents/skills/*/SKILL.md` | Loader-facing trigger metadata and core workflow instructions. |
| `.agents/skills/*/agents/openai.yaml` | UI metadata for skill pickers and prompt chips. |
| Generated references | `truecrime-cult-research/references/lane_registry.md` and `public-records-router/references/routing_matrix.md`; regenerate from `docs/registry/`. |

## Groups

| Group | Skills | Use |
| --- | --- | --- |
| Core | `truecrime-cult-research` | Case ledger, safety baseline, CLI script, templates, and export workflow. |
| Public record lanes | `corporate-financial-records`, `educational-path-records`, `geographical-location-intelligence`, `legal-court-records`, `licensing-professional-records`, `media-transcript-intelligence`, `missing-persons-case`, `property-location-records` | Domain-specific public-record collection and extraction. |
| Support lanes | `criminal-research`, `identity-resolution`, `public-records-router`, `source-capture-preservation` | Routing, preservation, identity review, and analytical support. |
| Review lanes | `claim-contradiction-audit`, `foia-open-records-planning`, `narrative-readiness-review`, `privacy-redaction-audit`, `source-independence-audit` | Contradiction, records-request, public-output, privacy, and corroboration review. |

## Update Checklist

1. Keep the skill folder name and `SKILL.md` frontmatter `name` identical.
2. Keep `description` as a single YAML string; quote it when it contains
   punctuation that can confuse stricter loaders.
3. Add or update `agents/openai.yaml` when a skill's purpose changes.
4. Update `docs/registry/` first for lane/template changes, then regenerate
   generated references.
5. Update `catalog.json` when a skill is added, removed, renamed, or moved
   between groups.
6. Run `moon run crk:test-governance` before committing.
