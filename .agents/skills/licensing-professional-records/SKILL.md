---
name: licensing-professional-records
description: Public-record workflow for researching professional licenses, certifications, board registrations, disciplinary actions, sanctions, suspensions, revocations, professional roles, and credential disputes, then adding source-traceable records to a CRK case file. Use when Codex needs to handle public licensing or professional-board records without inferring misconduct or competence from lookup data alone.
---

# Licensing Professional Records

## Operation vocabulary

Lane/template metadata is generated from `docs/registry/`; do not invent new lane IDs in this skill doc. Use operation `draft_extraction` with template `licensing-professional` for this lane; CLI fallback: `tcr.py draft-extraction ... --template licensing-professional`.


## Purpose

Use this skill to build a public, source-traceable licensing and professional-record packet for a CRK case. A license lookup proves only what the public record states; it does not prove competence, misconduct, employment, or identity without source support.

This skill extends the CRK case workflow; follow the active truecrime-cult-research safety rules for privacy, source grading, source spans, claims, and public export boundaries.

## Required Inputs

Establish these before extraction when possible:

- Person or organization name, jurisdiction, profession, license number, board/agency, date range, or disciplinary docket.
- Target case path, normally `tc-c-kit/data/cases/<case_slug>` in this wrapper repo.
- Research question: credential status, discipline, board certification, sanctions, employment eligibility, credential dispute, or public-role context.

If the person identity is ambiguous, route through `identity-resolution` before importing license claims.

## Workflow

1. **Resolve jurisdiction and profession.** Identify the relevant board, agency, certification body, or regulator.
2. **Collect official records.** Use source lanes from [source_lanes.md](references/source_lanes.md). Register each lookup page, order, disciplinary document, consent agreement, or official profile as a source.
3. **Preserve identifiers.** Capture license number, board name, disciplinary docket, order number, status date, and source spans.
4. **Extract cautiously.** Use [case_mapping.md](references/case_mapping.md) and `draft-extraction --template licensing-professional`.
5. **Review contradictions and identity.** Compare status dates, board orders, profile pages, appeals, and same-name candidates.
6. **Validate and audit.** Run validation and public-export audit before public use.

## Commands

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py add-source tc-c-kit/data/cases/<case_slug> \
  --title "<Board or license record title>" \
  --url "<official URL>" \
  --source-type government_record \
  --reliability-grade A \
  --notes "license/board; jurisdiction; license number or docket; status date"

python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID> --template licensing-professional
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction tc-c-kit/data/cases/<case_slug> tc-c-kit/data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json
python .agents/skills/truecrime-cult-research/scripts/tcr.py resolve-identities tc-c-kit/data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-public-export tc-c-kit/data/cases/<case_slug> --warn-only
```

## Extraction Rules

- Distinguish active, expired, suspended, revoked, surrendered, probationary, restricted, and unknown license statuses.
- Use `assertion_type: court_finding` only for board findings, consent orders, adjudicated sanctions, or court/regulator orders.
- Use `assertion_type: allegation` for complaints or pending charges; do not present them as findings.
- Do not publish home addresses, private workplaces, personal phone/email, full dates of birth, personal identifiers, complaint details involving private people, or minor information.
- Do not infer misconduct from a license lookup, name match, expired status, or board record without a source-stated disciplinary fact.

## Output Expectations

A completed licensing packet should leave the case with official source records, source spans for license/docket identifiers, entity records for the person/board/agency, claims for status or discipline facts, events for dated board actions, relationships such as `licensed_by` or `disciplined_by`, and privacy redactions where needed.
