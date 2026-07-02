---
name: legal-court-records
description: Public-record workflow for researching court cases, dockets, filings, orders, opinions, judgments, hearings, allegations, denials, court findings, parties, attorneys, judges, and litigation posture, then adding source-traceable legal records to a TRCR case file. Use when Codex needs to pull or organize public legal/court records without overstating allegations or exposing sealed/private details.
---

# Legal Court Records

## Operation vocabulary

Lane/template metadata is generated from `docs/lanes.json`; do not invent new lane IDs in this skill doc. Use operation `draft_extraction` with template `legal-court` for this lane; CLI fallback: `tcr.py draft-extraction ... --template legal-court`.


## Purpose

Use this skill to build a public, source-traceable legal record packet for a TRCR case. Treat court records as evidence for what the record says and when it said it; do not convert allegations into findings or procedural posture into guilt, liability, motive, or credibility.

This skill extends the TRCR case workflow; follow the active truecrime-cult-research safety rules for privacy, source grading, source spans, claims, and public export boundaries.

## Required Inputs

Establish these before extraction when possible:

- Court, jurisdiction, case number, party names, docket URL, document number, filing date, or citation.
- Date range and research question: party roles, timeline, allegations, denials, findings, disposition, appeals, bankruptcy, or related civil/criminal proceedings.
- Target case path, normally `tc-c-kit/data/cases/<case_slug>` in this wrapper repo.

If the case identity is ambiguous, record candidates and mark claims `unverified` until a public record ties the court, docket number, party, date, or filing to the target.

## Workflow

1. **Resolve the case.** Identify court, jurisdiction, case caption, docket/case number, filing date, and source URL or archive.
2. **Collect public source packets.** Use source lanes from [source_lanes.md](references/source_lanes.md). Register each docket page, filing, order, opinion, transcript, or strong legal article before extracting facts.
3. **Preserve locators.** Add docket item, document number, page, paragraph, exhibit, timestamp, or quote-offset locators as `source_spans`.
4. **Extract legal posture precisely.** Use [case_mapping.md](references/case_mapping.md). Separate allegations, denials, findings, orders, judgments, and appeals with `assertion_type`.
5. **Add parties and roles.** Add named public-role people and organizations only when the public record identifies them.
6. **Run contradiction checks.** Compare allegations, denials, findings, amendments, reversals, appeals, and later corrections.
7. **Validate and audit.** Run TRCR validation, contradiction audit, and public-export audit before using legal material in public outputs.

## Commands

Use the wrapper-local TRCR tool path and prefix case paths with `tc-c-kit/`:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py add-source tc-c-kit/data/cases/<case_slug> \
  --title "<Court, case, docket item, or filing title>" \
  --url "<official or archived URL>" \
  --source-type court_record \
  --reliability-grade A \
  --notes "court; case number; docket/document number; filing date; page or locator notes"

python .agents/skills/truecrime-cult-research/scripts/tcr.py preserve-source tc-c-kit/data/cases/<case_slug> <SOURCE_ID>
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID> --template legal-court
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction tc-c-kit/data/cases/<case_slug> tc-c-kit/data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-contradictions tc-c-kit/data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate tc-c-kit/data/cases/<case_slug>
```

## Extraction Rules

- Use `assertion_type: allegation` for pleadings, complaints, charges, motions, and claims framed as allegations.
- Use `assertion_type: denial` for answers, responses, statements denying allegations, acquittals, or contested assertions.
- Use `assertion_type: court_finding` only for findings, orders, judgments, verdicts, rulings, sentencing entries, or dispositions directly stated by the court record.
- Do not publish sealed, expunged, juvenile, victim/private-person contact, address, medical, financial identifier, or minor details.
- Do not infer that a party, witness, attorney, or co-defendant is guilty, liable, affiliated, or credible unless a cited source states that.
- Treat docket summaries and mirrors as useful locators; cite the underlying filing/order when available.

## Output Expectations

A completed legal packet should leave the case with source records, source spans, artifacts for key filings/orders, claims distinguished by assertion type, events for procedural milestones, relationships for source-stated legal roles, contradiction notes, and public-export redactions where needed.
