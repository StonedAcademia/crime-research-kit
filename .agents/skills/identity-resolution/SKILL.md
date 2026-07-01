---
name: identity-resolution
description: Public-record workflow for reviewing aliases, duplicate entities, ambiguous people or organizations, possible same-as/not-same-as matches, and entity merge candidates in a TRCR case file. Use when Codex needs to resolve identity evidence without auto-merging records, doxxing private people, or treating name matches as proof.
---

# Identity Resolution

## Purpose

Use this skill to review whether multiple TRCR entity records, names, aliases, or public-record references may describe the same person or organization. The output is a source-backed review packet, not an automatic merge.

This skill extends the TRCR case workflow; follow the active truecrime-cult-research safety rules for privacy, source grading, source spans, claims, and public export boundaries.

## Required Inputs

Establish these before review when possible:

- Target case path, normally `tc-c-kit/data/cases/<case_slug>` in this wrapper repo.
- Candidate names, aliases, entity IDs, organizations, dates, jurisdictions, public roles, or source IDs.
- Whether the goal is duplicate cleanup, alias review, not-same-as exclusion, or public-record disambiguation.

If the identity is ambiguous, keep the entity `status: candidate` or the claim `status: unverified`. Do not merge records until a human or later explicit task decides the merge.

## Workflow

1. **Inventory candidates.** Run `resolve-identities` to identify same-name/alias clusters and inspect source context.
2. **Collect identity anchors.** Use source lanes from [source_lanes.md](references/source_lanes.md). Prefer public records that tie a name to a role, organization, jurisdiction, date, or document.
3. **Draft an identity packet.** Use `draft-extraction --template identity-resolution` for sources that directly support or conflict with an identity match.
4. **Map evidence conservatively.** Use [case_mapping.md](references/case_mapping.md). Add identity claims, aliases, source spans, and possibly-same/not-same relationships only when a source supports them.
5. **Flag privacy.** Keep private-person, minor, address, school/workplace, family, medical, or contact details out of public exports.
6. **Validate and audit.** Run validation, dedupe, and public-export audit before using resolved identities in charts or scripts.

## Commands

Use the wrapper-local TRCR tool path and prefix case paths with `tc-c-kit/`:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py resolve-identities tc-c-kit/data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py dedupe tc-c-kit/data/cases/<case_slug> --record-type entities
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID> --template identity-resolution
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction tc-c-kit/data/cases/<case_slug> tc-c-kit/data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-public-export tc-c-kit/data/cases/<case_slug> --warn-only
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate tc-c-kit/data/cases/<case_slug>
```

## Resolution Rules

- A shared name is a lead, not proof of identity.
- Treat common names, initials, name changes, transliterations, and reused organizational names as high-risk until source anchored.
- Prefer source-stated identifiers that are public and relevant: case number, public office, corporate role, institution, jurisdiction, dates, publication byline, or official biography.
- Do not store private identifiers such as home address, phone, email, SSN, student ID, full DOB, personal financial identifier, or family details unless already central in a public-interest record and public export remains blocked.
- Use `possibly_same_as` only for review leads; use `not_same_as` when a source-backed conflict excludes a match.
- Set `public_export: false` for identity candidates until reviewed.

## Output Expectations

A completed identity packet should leave the case with a candidate report, source spans for identity anchors, identity claims with confidence/status, alias notes, possibly-same/not-same relationships where appropriate, privacy flags, and no silent entity merges.
