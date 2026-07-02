---
name: educational-path-records
description: Public-record workflow for researching an individual's education history, schools attended, degrees, training, credentials, academic appointments, alumni claims, student-era events, and institution affiliations, then adding source-traceable entities, claims, relationships, events, artifacts, and sources to a TRCR case file. Use when Codex needs to pull educational paths from public records, official biographies, court records, archival sources, professional licensing records, academic publications, or reputable reporting while avoiding private education records, doxxing, and unsupported credential claims.
---

# Educational Path Records

## Operation vocabulary

Lane/template metadata is generated from `docs/registry/`; do not invent new lane IDs in this skill doc. Use operation `draft_extraction` with template `education` for this lane; CLI fallback: `tcr.py draft-extraction ... --template education`.


## Purpose

Use this skill to build a public, source-traceable educational path packet for an individual in a TRCR case. Capture what sources directly state about education, training, degrees, credentials, institutions, academic roles, and student-era events. Do not infer ideology, affiliation, misconduct, class rank, attendance, or degree completion from proximity or vague biographical wording.

This skill extends the TRCR case workflow; follow the active truecrime-cult-research safety rules for privacy, source grading, claims, and public export boundaries.

## Required Inputs

Establish these before extraction when possible:

- Person name, aliases, date range, public role, and target case path.
- Research question: education timeline, degree verification, training, academic appointments, student organizations, institutional influence, credential contradictions, or public claims about attendance.
- Source boundaries: public records only, user-provided lawful material, or a specific archive/report.

If the person identity is ambiguous, create candidate entities and mark claims `unverified` until public records tie the name, date range, institution, or public role to the target person.

## Hard Boundaries

- Do not seek, reveal, or compile private student records, transcripts, grades, disciplinary records, student IDs, account IDs, precise dorm/home addresses, private emails, or non-public school records.
- Do not expose information about minors unless already central to a widely reported public record and essential to the public-interest purpose.
- Treat yearbooks, alumni pages, social posts, class notes, and directories as sensitive leads when they identify private people or minors.
- Do not contact schools, classmates, family members, teachers, or private individuals.
- Do not convert co-attendance, same class year, same club, or same institution into friendship, membership, mentorship, ideology, or influence without a source saying so.

## Workflow

1. **Resolve the person and scope.** Identify the public person and aliases. Record uncertainty where names are common.
2. **Collect source packets.** Use source lanes from [source_lanes.md](references/source_lanes.md). Register sources before extracting facts.
3. **Separate claim types.** Distinguish attended, enrolled, graduated, degree awarded, studied subject, trained at, taught at, researched at, affiliated with, honorary degree, and claimed-but-unverified.
4. **Map to case ledgers.** Use [case_mapping.md](references/case_mapping.md) for entities, claims, events, relationships, and artifacts.
5. **Check contradictions and chronology.** Compare official biographies, resumes, court filings, institutional pages, publication bios, licensing pages, and reporting. Preserve stale/changed claims in notes.
6. **Run privacy review.** Mark private-person/minor details `public_export: false`; redact addresses and non-public classmates.
7. **Validate the case.** Run TRCR validation and report commands after import.

## Commands

Use the wrapper-local TRCR tool path and prefix case paths with `tc-c-kit/`:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py add-source tc-c-kit/data/cases/<case_slug> \
  --title "<Public education source title>" \
  --url "<official or archived URL>" \
  --source-type government_record \
  --reliability-grade A \
  --notes "education-path record; exact institution/source date/page"

python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID>
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction tc-c-kit/data/cases/<case_slug> tc-c-kit/data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate tc-c-kit/data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py report tc-c-kit/data/cases/<case_slug>
```

Source-type defaults:

- `government_record`: court filings, legislative bios, agency bios, licensing records, official public records.
- `official_report`: institutional annual report, official biography, accreditation/licensing board report.
- `academic`: journal article, dissertation catalog, institutional repository, faculty profile, publication bio.
- `archive`: yearbook/archive/catalog only when public and relevant.
- `news_article`: reputable reporting about education history or credential disputes.
- `other`: personal website, campaign bio, resume, social profile, database page; usually self-reported or lead-only.

## Extraction Rules

- Quote the source's level of certainty: "attended," "graduated," "received," "studied," "trained," "was listed as," "claimed," "was described as."
- Do not upgrade "attended" to "graduated" or "studied at" to "degree awarded."
- Capture institution name as it appeared at the time and note later renames or mergers.
- Capture date precision honestly: exact date, year, approximate period, or unknown.
- For public persons, keep education facts relevant to the case question; avoid building exhaustive school social graphs.
- For student organizations, extract membership or leadership only when directly stated by a public source and relevant.
- For academic publications, distinguish author affiliation at publication time from degree/training history.
- For professional credentials, separate education from licensure, certification, board certification, apprenticeship, military training, or honorary awards.
- For credential disputes, include the claim, the source asserting it, the source contradicting it, and status `disputed` or `unverified`.

## Output Expectations

A completed educational path packet should leave the case with:

- Source records for every biography, filing, archive, institutional page, article, or public record used.
- Entity records for the person and relevant institutions.
- Claims for specific education/training/credential assertions.
- Relationships for attended/graduated_from/taught_at/trained_at/affiliated_with links.
- Events for enrollment, graduation, appointment, resignation, publication, credential grant/revocation, or public credential dispute.
- Artifacts for important documents such as biographies, CVs, court exhibits, yearbook pages, dissertations, catalog records, or licensing records.
- Notes preserving uncertainty, contradictions, source dates, institutional name changes, and privacy redactions.
