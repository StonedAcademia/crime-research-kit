---
name: missing-persons-case
description: "TRCR workflow for identifying source-supported missing-person candidates by name, alias, location, date range, last-known event, related people, vehicles, organizations, and public record context, then adding conservative leads, claims, events, places, relationships, source spans, and privacy flags to a case file. Use when Codex needs to compare a subject or event against public missing-person records, bulletins, reporting, NamUs/NCMEC-style listings, law-enforcement releases, unidentified-person records, or found/recovered status updates without doxxing or vigilante contact."
---

# Missing Persons Case

## Purpose

Use this skill to identify and structure missing-person candidates that may be relevant to a TRCR case. A candidate match is a lead until public sources support identity, date, location, and status. Do not contact relatives, witnesses, law enforcement, schools, employers, or private people.

This skill extends the TRCR case workflow; follow the active truecrime-cult-research safety rules for privacy, source grading, source spans, claims, and public export boundaries.

## Required Inputs

Establish these before extraction when possible:

- Target case path, normally `tc-c-kit/data/cases/<case_slug>` in this wrapper repo.
- Name, aliases, initials, nickname, or unidentified-person descriptor.
- Broad location, jurisdiction, last-known place, event location, or travel route.
- Date or date range for disappearance, report, sighting, recovery, or status update.
- Known links such as related entities, vehicles, organizations, case numbers, source IDs, or event IDs.

If the subject is a minor, a living private person, or an ambiguous identity, keep records `public_export: false` until privacy review and source support are complete.

## Workflow

1. **Define the match question.** State whether you are searching by name, alias, location/time window, event proximity, vehicle, institution, or unidentified-person profile.
2. **Route identity ambiguity first.** Use `identity-resolution` for name collisions, alias conflicts, possible same-as records, and unidentified-person comparisons.
3. **Collect public sources.** Use [source_lanes.md](references/source_lanes.md). Prioritize official bulletins, public missing-person databases, law-enforcement releases, court/coroner records when public, and strong local reporting.
4. **Score candidate relevance.** Use [candidate_matching.md](references/candidate_matching.md). Treat all matches as lead-only until source-backed.
5. **Draft a missing-person packet.** Use `draft-extraction --template missing-persons` and map rows with [case_mapping.md](references/case_mapping.md).
6. **Register status updates.** Capture missing, located, recovered, unidentified, deceased, correction, misidentification, or retraction status as dated claims/events with source spans.
7. **Audit before public output.** Run validation, contradiction/source-independence checks where relevant, and public-export/privacy audits before publishing any missing-person details.

## Commands

Use the wrapper-local TRCR tool path and prefix case paths with `tc-c-kit/`:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py plan-public-records tc-c-kit/data/cases/<case_slug> \
  --subject "<name, alias, location, date range, vehicle, or event>" \
  --lane missing-persons

python .agents/skills/truecrime-cult-research/scripts/tcr.py add-source tc-c-kit/data/cases/<case_slug> \
  --title "<Official bulletin, database entry, local report, or status update>" \
  --url "<public URL>" \
  --source-type government_record \
  --reliability-grade A \
  --notes "missing-person lead; jurisdiction/date/status; privacy review needed"

python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID> --template missing-persons
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction tc-c-kit/data/cases/<case_slug> tc-c-kit/data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-public-export tc-c-kit/data/cases/<case_slug> --warn-only
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate tc-c-kit/data/cases/<case_slug>
```

## Extraction Rules

- Record the source wording for missing, endangered, runaway, voluntarily missing, located, recovered, unidentified, deceased, or misidentified statuses.
- Use broad place records when exact last-known locations are private homes, schools, shelters, workplaces, or minor-related locations.
- Distinguish date missing, date reported, last seen, last contact, sighting, recovery, identification, and publication dates.
- Do not infer foul play, trafficking, cult involvement, criminal responsibility, or direct case relevance from proximity alone.
- Do not publish private contact details, family-member identities, tip-line data beyond official public contact channels, current residences, school details, medical details, or minor-sensitive data.
- Mark uncertain matches as `status: unverified`, `confidence <= 0.4`, `assertion_type: lead_only`, and `public_export: false`.

## Output Expectations

A completed missing-person packet should leave public sources, candidate entities, broad places, dated disappearance/status events, source-supported claims, source spans for bulletin/database/report locators, artifacts for bulletins or case pages, relationships only when source-stated, and redactions for private-person or minor-sensitive details.
