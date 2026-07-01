---
name: corporate-financial-records
description: Public-record workflow for researching corporations, nonprofits, banks, shell companies, bankruptcies, investments, ownership, directors, officers, and board members, then adding source-traceable entities, claims, relationships, events, artifacts, and sources to a TRCR case file. Use when Codex needs to pull public financial/corporate records, SEC or state filings, bankruptcy dockets, investment disclosures, beneficial ownership leads, or board rosters without inferring misconduct from proximity.
---

# Corporate Financial Records

## Purpose

Use this skill to build a public, source-traceable corporate record packet for a TRCR case. Prioritize official filings and court/government records, preserve uncertainty, and add only source-supported corporate facts to the case ledgers.

This skill extends the TRCR case workflow; follow the active truecrime-cult-research safety rules for privacy, source grading, claims, and public export boundaries.

## Required Inputs

Establish these before extraction when possible:

- Corporation/legal entity name, ticker, CIK, EIN, registration number, or jurisdiction.
- Date range and research question: board roster, bankruptcy, investment/funding, ownership/control, subsidiaries, financial condition, litigation, or transaction history.
- Target case path, normally `tc-c-kit/data/cases/<case_slug>` in this wrapper repo.

If the company identity is ambiguous, create candidate entities and mark claims `unverified` until a filing ties the alias, ticker, jurisdiction, or address to the target.

## Workflow

1. **Resolve the entity.** Search official registries first. Record legal name, aliases, ticker/CIK, jurisdiction, status, registered entity type, and source IDs.
2. **Collect official source packets.** Use source lanes from [source_lanes.md](references/source_lanes.md). Register each filing, docket, annual report, or registry page as a source before extracting facts.
3. **Extract only direct facts.** Use the filing's wording for claims. Do not infer fraud, control, membership, motive, shell-company purpose, or hidden ownership unless the source says it.
4. **Add people and organizations.** Board members, directors, officers, investors, creditors, debtors, subsidiaries, auditors, trustees, and committees are entities only when named in public filings or strong reporting.
5. **Add relationships and events.** Map records to TRCR ledgers using [case_mapping.md](references/case_mapping.md). Directors/officers/investors become relationships; bankruptcy filings, financings, mergers, delistings, and appointments become events.
6. **Run contradiction and currency checks.** Compare board rosters and financial facts across filing dates. Mark stale or superseded facts in notes; avoid merging old and current boards.
7. **Validate the case.** Run TRCR validation and report commands after import.

## Commands

Use the wrapper-local TRCR tool path and prefix case paths with `tc-c-kit/`:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py add-source tc-c-kit/data/cases/<case_slug> \
  --title "<Filing or docket title>" \
  --url "<official URL>" \
  --source-type government_record \
  --reliability-grade A \
  --notes "corporate financial record; exact filing date and accession/docket number"

python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID>
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction tc-c-kit/data/cases/<case_slug> tc-c-kit/data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate tc-c-kit/data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py report tc-c-kit/data/cases/<case_slug>
```

Prefer `source_type: government_record` for SEC, state registry, court, bankruptcy, Companies House, or regulator records; `court_record` for docket/case filings; `official_report` for audited annual reports and regulator reports; `news_article` for reputable reporting; `other` for secondary corporate databases used as leads only.

## Extraction Rules

- Treat public filings as evidence for what the filing states and when it stated it. A filing can still be stale, amended, or self-reported.
- Include filing identifiers in source notes: accession number, form type, docket/case number, jurisdiction, file date, period end, page/table, and archive URL when available.
- For directors/officers, capture role title and date/period from the filing. Do not add home addresses, signatures, birth dates, personal phone/email, family details, or non-public employers.
- For investments, distinguish investor, issuer, lender, creditor, beneficial owner, underwriter, fund manager, and portfolio company. Do not collapse them into one relationship.
- For bankruptcies, distinguish debtor, creditor, trustee, examiner, committee, purchaser, lender/DIP lender, and affiliate. Extract claim amounts only when public and relevant.
- Mark beneficial ownership, control, or affiliation claims `single_source` unless corroborated by another independent official filing or strong secondary source.
- Use `public_export: false` for records involving private persons, addresses, account numbers, non-public creditors, employees not central to the public-interest story, or sensitive financial identifiers.

## Output Expectations

A completed corporate packet should leave the case with:

- Source records for every filing/docket/report used.
- Entity records for the corporation and named public-role people or organizations.
- Claims for specific financial facts, board membership facts, bankruptcy facts, and investment facts.
- Relationships for board/officer/investor/creditor/subsidiary/ownership links.
- Events for dated filings, bankruptcies, funding rounds, mergers, appointments, resignations, and other material corporate actions.
- Artifacts for important filings such as proxy statements, petitions, annual reports, plans, schedules, and transaction agreements.
- Notes preserving contradictions, amended filings, stale rosters, and privacy redactions.
