---
name: foia-open-records-planning
description: Public-records request planning workflow for FOIA, state open-records, sunshine-law, agency records, request wording, exemptions, fee waivers, response tracking, appeals, and released-record intake into a CRK case. Use when Codex needs to plan lawful public-record requests without treating the request plan as evidence.
---

# FOIA Open Records Planning

## Operation vocabulary

Lane/template metadata is generated from `docs/registry/`; do not invent new lane IDs in this skill doc. Use operation `draft_extraction` with template `foia-open-records` for this lane; CLI fallback: `tcr.py draft-extraction ... --template foia-open-records`.


## Purpose

Use this skill to plan public-records requests for a CRK case. A request plan is a lead and workflow artifact; it does not prove records exist or support factual claims until responsive records are received, registered, preserved, extracted, and cited.

This skill extends the CRK case workflow; follow the active truecrime-cult-research safety rules for privacy, source grading, source spans, claims, and public export boundaries.

## Required Inputs

Establish these before planning when possible:

- Subject, agency/public body, jurisdiction, date range, likely custodians, and requested record categories.
- Target case path, normally `tc-c-kit/data/cases/<case_slug>` in this wrapper repo.
- Whether the request is for source discovery, contradiction checking, timeline support, legal records, property records, licensing records, or media/transcript records.

Do not request private-person contact details, medical details, financial identifiers, minor records, or exempt/private material unless the public-interest basis is explicit and lawful.

## Workflow

1. **Scope the request.** Identify agency, jurisdiction, records, date range, exclusions, and likely exemptions.
2. **Create a request plan.** Run `plan-open-records` and review [request_checklist.md](references/request_checklist.md).
3. **Track the request.** Store request ID, submission date, due date, status, fee estimate, and appeal deadline in notes or the plan artifact.
4. **Register responses as sources.** When records arrive, use `add-source` or `ingest-url`, then `preserve-source`.
5. **Extract only received records.** Use `draft-extraction --template foia-open-records` for request/response metadata and route released records to the appropriate content skill.
6. **Audit before public use.** Run privacy-redaction, source-independence, and narrative-readiness review as needed.

## Commands

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py plan-open-records tc-c-kit/data/cases/<case_slug> \
  --subject "<subject>" \
  --agency "<agency or office>" \
  --jurisdiction "<jurisdiction>" \
  --date-range "<date range>" \
  --record "<record category>"

python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID> --template foia-open-records
```

## Output Expectations

A completed planning pass should leave an open-records JSON plan under `staging/candidates/`, request wording, privacy exclusions, an appeal tracker, and no evidence claims until responsive records are received and imported.
