---
name: public-records-router
description: Public-record source-planning workflow for routing a CRK case subject across legal, corporate, education, licensing, media/transcript, missing-person, geographical-location, criminal-research, property/location, source-preservation, identity-resolution, and contradiction-review lanes. Use when Codex needs to decide which public records to seek, in what order, and with what safety constraints before extraction.
---

# Public Records Router

## Operation vocabulary

Lane/template metadata is generated from `docs/registry/`; do not invent new lane IDs in this skill doc. Use operation `draft_extraction` with template `public-records-router` for this lane; CLI fallback: `crk-ledger draft-extraction ... --template public-records-router`.


## Purpose

Use this skill to turn a subject or research question into a public-record source plan. The router creates leads and lane choices, not evidence. Evidence starts only after sources are registered, preserved, extracted, and imported into the CRK ledger.

This skill extends the CRK case workflow; follow the active truecrime-cult-research safety rules for privacy, source grading, claims, and public export boundaries.

## Required Inputs

Establish these before routing when possible:

- Subject name, organization, place, case, event, or question.
- Target case path, normally `tc-c-kit/data/cases/<case_slug>` in this wrapper repo.
- Known jurisdictions, dates, aliases, agencies, institutions, source IDs, or constraints.

If the subject is ambiguous, route to `identity-resolution` before collecting sensitive or person-specific records.

## Workflow

1. **Create or open the case.** Route plans belong inside a CRK case, even when no sources have been imported yet.
2. **Generate the source plan.** Run `plan-public-records` with the subject and optional forced lanes.
3. **Choose lanes.** Use [routing_matrix.md](references/routing_matrix.md). Load the specific skill named by the selected lane before extraction.
4. **Register sources first.** Use `ingest-url` or `add-source`, then `preserve-source` when local artifacts or archive URLs matter.
5. **Draft lane-specific packets.** Use `draft-extraction --template <lane-template>` and fill only source-supported records.
6. **Audit before public output.** Run validation, contradiction/source-independence checks where relevant, and public-export audit.

## Commands

Use the wrapper-local CRK tool path and prefix case paths with `tc-c-kit/`:

```bash
crk-ledger plan-public-records tc-c-kit/data/cases/<case_slug> \
  --subject "<person, org, case, place, or event>" \
  --question "<optional research question>"

crk-ledger draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID> --template public-records-router
```

Use `--lane licensing-professional`, `--lane media-transcript`, or another lane to force a plan for a known domain.

## Routing Rules

- Use official/public primary sources first, then strong secondary reporting.
- Route legal allegations through `legal-court-records` and contradiction review before public narration.
- Route licenses and discipline through `licensing-professional-records`; do not infer competence or misconduct from lookup presence alone.
- Route videos, hearings, podcasts, and interviews through `media-transcript-intelligence`; timestamped claims still need review.
- Route missing-person, last-seen, located/recovered, and unidentified-person candidate work through `missing-persons-case`; candidate matches are lead-only until sourced.
- Route evidence-item geography, event maps, routes, sightings, and locations of interest through `geographical-location-intelligence`; exact private or weak-lead locations default to non-public.
- Route M.O., victimology, offense-pattern, behavioral-signature, escalation, and forensic personality analysis through `criminal-research`; diagnostic or weak profile claims default to non-public.
- Route parcels, deeds, permits, maps, and addresses through `property-location-records`; private addresses default to non-public.
- Use `source-capture-preservation` for archive, hash, and provenance questions.

## Output Expectations

A completed router pass should leave a JSON source-plan report under `staging/candidates/`, lane-specific next commands, source-query suggestions, and no evidence claims unless a later source extraction imports them.
