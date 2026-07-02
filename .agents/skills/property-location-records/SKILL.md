---
name: property-location-records
description: Public-record workflow for researching property, parcel, deed, permit, zoning, map, facility, campus, address-sensitive, and location-history records, then adding source-traceable places, claims, events, artifacts, and relationships to a TRCR case file. Use when Codex needs property/location records while redacting private addresses and avoiding doxxing.
---

# Property Location Records

## Operation vocabulary

Lane/template metadata is generated from `docs/registry/`; do not invent new lane IDs in this skill doc. Use operation `draft_extraction` with template `property-location` for this lane; CLI fallback: `tcr.py draft-extraction ... --template property-location`.


## Purpose

Use this skill to build public, source-traceable property and location packets for a TRCR case. Property records are often public but still privacy-sensitive; do not publish private home addresses, precise locations of private people, or minor-related locations unless central to a widely reported public record and clearly justified.

This skill extends the TRCR case workflow; follow the active truecrime-cult-research safety rules for privacy, source grading, source spans, claims, and public export boundaries.

## Required Inputs

Establish these before extraction when possible:

- Jurisdiction, parcel ID, facility name, organization, owner/entity, deed/instrument number, permit number, map reference, or broad location.
- Target case path, normally `tc-c-kit/data/cases/<case_slug>` in this wrapper repo.
- Research question: ownership history, facility location, permit timeline, land-use context, public institution, corporate property, or address redaction review.

If a record points to a private residence or private person, keep the place and related claims `public_export: false` unless public-interest justification is explicit.

## Workflow

1. **Define public-interest need.** Decide whether exact location is necessary or whether a vague area/jurisdiction is enough.
2. **Collect official records.** Use source lanes from [source_lanes.md](references/source_lanes.md). Register assessor, recorder, deed, permit, zoning, GIS, map, or archive sources before extraction.
3. **Preserve record identifiers.** Capture parcel IDs, deed book/page, instrument numbers, permit numbers, map sheet, and source spans.
4. **Extract with redaction defaults.** Use [case_mapping.md](references/case_mapping.md) and `draft-extraction --template property-location`.
5. **Cross-check entity ownership.** Route LLC/corporate ownership to `corporate-financial-records` and ambiguous names to `identity-resolution`.
6. **Audit public export.** Run public-export audit before publishing any property or location output.

## Commands

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py add-source tc-c-kit/data/cases/<case_slug> \
  --title "<Assessor, recorder, permit, map, or facility record>" \
  --url "<official URL>" \
  --source-type government_record \
  --reliability-grade A \
  --notes "property/location; jurisdiction; parcel/instrument/permit identifier; redaction review needed"

python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID> --template property-location
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction tc-c-kit/data/cases/<case_slug> tc-c-kit/data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-public-export tc-c-kit/data/cases/<case_slug> --warn-only
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate tc-c-kit/data/cases/<case_slug>
```

## Extraction Rules

- Prefer facility, jurisdiction, parcel, or vague-area place records over exact private addresses.
- Use `public_export: false` for home addresses, current private residences, minor-related places, shelter/safe-house locations, private workplaces, and non-central family property.
- Add redaction records for sensitive address/location fields even when the source is public.
- Distinguish owner of record, mailing address, registered agent, trustee, permit applicant, operator, occupant, and facility.
- Do not infer ownership, control, residence, or presence from proximity to a property record without source support.

## Output Expectations

A completed property/location packet should leave source records, place records, source spans for parcel/deed/permit/map locators, artifacts for deeds/maps/permits, claims about public-record facts, events for transfers/permits/inspections, relationships such as `owned_by` or `operated_at`, and redactions for private location details.
