---
name: truecrime-cult-research
description: Data-first true crime and high-control group/cult-origin research workflow. Use for finding and organizing public news articles, eyewitness accounts, official records, people, places, things, events, claims, relationships, contradictions, source reliability, privacy review, and Manim-ready exports. Do not use for doxxing, harassment, private-person targeting, vigilante investigation, or unsourced accusations.
---

# True Crime / Cult-Origin Research Skill

## Purpose

Use this skill when the user wants to research a true-crime case, cult/high-control group origin, related members, founders, victims/survivors, witnesses, places, objects/artifacts, events, public records, source evidence, contradictions, and visual outputs.

The goal is not to produce gossip. The goal is to create a structured, source-traceable case file that can power scripts, evidence boards, timelines, network graphs, and Manim scenes.

## Adjacent skill routing

Use this skill as the case-ledger and safety baseline. Route topic-heavy lanes
to the more specific skill when the research question is mainly about that
domain:

- Use `corporate-financial-records` for corporations, nonprofits, banks, shell companies, bankruptcies, investments, ownership/control, directors, officers, boards, SEC/state filings, court or bankruptcy dockets, transactions, and financial-record packets.
- Use `educational-path-records` for schools attended, degrees, training, credentials, academic appointments, alumni claims, student-era events, institution affiliations, and public credential disputes.
- Use `legal-court-records` for public dockets, filings, court orders, opinions, judgments, hearings, party roles, allegations, denials, court findings, and litigation posture.
- Use `identity-resolution` for aliases, duplicate entities, ambiguous public-record identities, candidate merges, entity disambiguation, and identity-conflict review.
- Use `source-capture-preservation` for source capture metadata, archive URLs, local raw/text preservation, hashes, provenance gaps, and source-preservation reports.
- Use `claim-contradiction-audit` for corrections, retractions, denials, court findings that narrow claims, contradictory source accounts, and claim-status review.
- Use `public-records-router` when the subject needs a source-lane plan across multiple public-record domains before extraction.
- Use `licensing-professional-records` for professional licenses, certifications, board registrations, disciplinary actions, sanctions, suspensions, revocations, and credential-status disputes.
- Use `media-transcript-intelligence` for interviews, podcasts, hearings, broadcasts, documentaries, captions, transcripts, timestamped speaker claims, and quote locators.
- Use `property-location-records` for property, parcel, deed, permit, zoning, map, facility, campus, and address-sensitive location records.
- Use `missing-persons-case` for missing-person, unidentified-person, last-seen, reported-missing, located/recovered, public bulletin, status-update, and candidate-match research.
- Use `geographical-location-intelligence` for evidence-item geography, event maps, routes, sightings, map/exhibit locators, locations of interest, and public-safe map packets.
- Use `foia-open-records-planning` for FOIA, open-records, sunshine-law, agency-records request wording, response tracking, exemptions, fee waivers, and appeal planning.
- Use `narrative-readiness-review` before public scripts, reports, videos, timelines, Manim exports, or evidence boards.
- Use `privacy-redaction-audit` for private-person, minor, address/contact, medical, financial, weak allegation, and public-export redaction blockers.
- Use `source-independence-audit` for same-source chains, wire copy, press-release repetition, shared provenance, and overstated corroboration.

For mixed cases, create or open the TRCR case first, then use the adjacent skill
to produce source-traceable entities, claims, events, relationships, artifacts,
and notes back into the same case. Do not infer misconduct, membership,
influence, or hidden control from proximity, co-attendance, shared boards, or
financial structure.

## Non-negotiable safety and ethics rules

1. Use only public-interest and publicly available sources unless the user provides lawful private material they have permission to analyze.
2. Do not reveal or compile private-person contact info, home addresses, private family details, school/workplace details, medical details, financial identifiers, or information about minors unless already central to a widely reported public record and essential to the educational purpose.
3. Do not infer guilt, criminal responsibility, membership, motive, or intent from proximity. Record inference as hypothesis only, not fact.
4. Do not call a person a suspect, perpetrator, cult member, accomplice, or person of interest unless a cited source uses that label. Store the exact wording and source ID.
5. Treat eyewitness accounts as claims, not automatically as facts. Capture who said it, when, whether it was firsthand, whether it was corroborated, and what source carried it.
6. Search for contradictions, corrections, retractions, and disconfirming sources.
7. AI-generated summaries, social-media rumors, and unsourced forum posts are not evidence. They can be leads only.
8. Mark uncertain claims as `single_source`, `disputed`, `unverified`, or `excluded_from_public_script` rather than forcing certainty.

## Required evidence chain

Every public/video-ready point must trace through this chain:

```text
claim_id → claim text → source_ids → source grade → confidence/status → privacy review → export
```

If the chain is incomplete, do not put the claim in the public-facing script or Manim export except as explicitly unknown/disputed.

## Standard workflow

### 1. Create or open a case workspace

If a case folder does not exist, run:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py init-case tc-c-kit/data/cases/<case_slug> --title "<Case Title>"
```

### 2. Build a source-discovery plan

Use at least these search lanes when web search is available:

- `seed`: the case/group/person name with broad context.
- `local_news`: local newspapers, regional TV, local archives, dates, towns.
- `national_news`: major news coverage and later retrospectives.
- `eyewitness`: terms such as interview, witness, survivor, former member, testimony, affidavit, deposition, memoir, oral history, documentary transcript.
- `official_records`: court, police/public report, coroner/medical examiner where lawful and public, government archive, nonprofit archive, official press release.
- `contradictions`: correction, retraction, disputed, hoax, debunked, lawsuit, appeal, overturned, misidentified.
- `context`: scholarly or expert context on high-control groups, new religious movements, coercive control, charismatic authority, or the specific era/location.

Prioritize primary/official and strong secondary sources over repeat coverage.

If the plan is primarily corporate/financial, education-path, legal/court,
identity-resolution, source-preservation, contradiction-audit, licensing,
media/transcript, property/location, missing-persons, geographical-location,
public-record routing, open-records
planning, narrative-readiness, privacy-redaction, or source-independence
research, load the routed skill named above and use its source lanes and
extraction mapping.

### 3. Ingest each source

For each promising public URL, run:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py ingest-url tc-c-kit/data/cases/<case_slug> "<URL>" --source-type news_article --reliability-grade B
```

For a source that cannot be downloaded, manually register it:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py add-source tc-c-kit/data/cases/<case_slug> \
  --title "<Title>" \
  --url "<URL or path>" \
  --source-type eyewitness_account \
  --reliability-grade C \
  --notes "manual registration; transcript needed"
```

### 4. Draft extraction packets

For each source with text:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID>
```

Then read the source text and fill the staged JSON packet. Extract only what the source directly supports. Use `references/controlled_vocabularies.md` and add `source_spans` locators when a claim, quote, event, relationship, or event link needs page/paragraph/timestamp support.

Use `--template legal-court`, `--template identity-resolution`,
`--template source-capture`, `--template claim-contradiction`,
`--template public-records-router`, `--template licensing-professional`,
`--template media-transcript`, `--template property-location`,
`--template missing-persons`, `--template geographical-location`,
`--template foia-open-records`, `--template narrative-readiness`,
`--template privacy-redaction`, or `--template source-independence` when
the source is primarily in one of those adjacent lanes.

### 5. Extract structured records

Fill these arrays in the staged extraction JSON:

- `entities`: people, organizations, groups, publications, objects, vehicles, documents, institutions.
- `places`: towns, buildings, roads, properties, institutional locations, vague regions.
- `artifacts`: physical/digital things such as letters, manifestos, photos, weapons, vehicles, recordings, reports. Do not include illegal acquisition instructions or sensitive operational details.
- `claims`: source-supported assertions, including quotes and allegations.
- `events`: dated or approximate events.
- `event_links`: source-supported or explicitly marked co-mention links between one entity and one event.
- `relationships`: founded, led, recruited, witnessed, lived_at, worked_for, affiliated_with, reported_to, accused_by, charged_with, convicted_of, etc.
- `quotes`: short exact quotes only when needed for claim support.

Use neutral language. Preserve uncertainty.

### 6. Import, validate, and report

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction tc-c-kit/data/cases/<case_slug> tc-c-kit/data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate tc-c-kit/data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py report tc-c-kit/data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-manim tc-c-kit/data/cases/<case_slug>
```

### 7. Run privacy review

Before public exports, review:

- Living private persons.
- Minors.
- Private addresses and contact details.
- Non-public relatives.
- Medical/mental-health details.
- Graphic or sensational details.
- Uncharged allegations.

If uncertain, mark the record with `privacy_level: private_person` and `public_export: false`.

## Reliability grade rubric

Use `references/source_quality_rubric.md`.

Default grades:

- `A`: primary/official/contemporaneous source: court record, official report, original transcript, archived primary document.
- `B`: strong secondary source: major investigative reporting, documented book, peer-reviewed/scholarly context, reputable local reporting with named sourcing.
- `C`: testimonial or interpretive source: eyewitness interview, memoir, documentary, single-source article.
- `D`: weak lead-only source: unsourced blog/forum/wiki/social media, repeated internet claim, unattributed clip.
- `X`: exclude as evidence: AI summary, rumor, no provenance, content that appears fabricated or unlawfully obtained.

## Reference docs

- `references/research_workflow.md`: case workflow, research action logging, dedupe, source independence, and public-export audit conventions.
- `references/extraction_prompt.md`: source-packet extraction instructions.
- `references/controlled_vocabularies.md`: enum values, `assertion_type`, citation locator, and dedupe conventions.
- `references/topic_extraction_templates.md`: baseline, corporate/financial, education-path, missing-persons, geographical-location, Phase 1, Phase 2, and Phase 3 extraction checklists.
- `references/source_quality_rubric.md`: source grading and independence checks.
- `references/privacy_safety_rules.md`: redaction and public-output rules.
- Phase 1 adjacent skills: `legal-court-records`, `identity-resolution`, `source-capture-preservation`, and `claim-contradiction-audit`.
- Phase 2 adjacent skills: `public-records-router`, `licensing-professional-records`, `media-transcript-intelligence`, and `property-location-records`.
- Additional investigation skills: `missing-persons-case` and `geographical-location-intelligence`.
- Phase 3 adjacent skills: `foia-open-records-planning`, `narrative-readiness-review`, `privacy-redaction-audit`, and `source-independence-audit`.

## Prompt patterns for Codex

### Full case-map prompt

```text
Use the $truecrime-cult-research skill.
Create a new case workspace for [case/group].
Find public news articles, eyewitness accounts, and official records about the origins and early network.
For every source, ingest/register it, extract entities/events/claims/relationships/places/artifacts, flag contradictions, and export a Manim-ready timeline and relationship graph CSV.
Do not publish private-person details. Do not infer guilt or membership without a cited source.
```

### Corporate/financial routing prompt

```text
Use the $truecrime-cult-research skill and route the corporate/financial packet through corporate-financial-records.
Add public filings, dockets, official records, and strong reporting to tc-c-kit/data/cases/[case_slug].
Extract only source-stated organizations, officers/directors, ownership or bankruptcy facts, claims, events, relationships, artifacts, and source_spans.
Do not infer fraud, hidden control, misconduct, or membership from proximity or structure.
```

### Education-path routing prompt

```text
Use the $truecrime-cult-research skill and route the education packet through educational-path-records.
Add public sources about [person]'s schools, degrees, training, credentials, academic appointments, or institutional affiliations to tc-c-kit/data/cases/[case_slug].
Preserve the source wording, distinguish attended from graduated, and do not seek private student records.
```

### Legal/court routing prompt

```text
Use the $truecrime-cult-research skill and route the legal packet through legal-court-records.
Add public court sources about [case/person/org] to tc-c-kit/data/cases/[case_slug].
Preserve docket item, filing, page, paragraph, and court-finding locators, and distinguish allegations, denials, and findings.
```

### Identity-resolution routing prompt

```text
Use the $truecrime-cult-research skill and route the identity packet through identity-resolution.
Review aliases and ambiguous entities in tc-c-kit/data/cases/[case_slug] without merging records automatically.
Write identity candidates with source support, privacy flags, and unresolved conflicts.
```

### Source-capture routing prompt

```text
Use the $truecrime-cult-research skill and route source preservation through source-capture-preservation.
Capture or verify source metadata, archive URLs, raw/text paths, checksums, and provenance gaps for tc-c-kit/data/cases/[case_slug].
```

### Contradiction-audit routing prompt

```text
Use the $truecrime-cult-research skill and route contradiction review through claim-contradiction-audit.
Audit claims in tc-c-kit/data/cases/[case_slug] for corrections, retractions, denials, court findings, and conflicting source accounts.
```

### Public-records router prompt

```text
Use the $truecrime-cult-research skill and route public-record planning through public-records-router.
Build a source-lane plan for [subject] in tc-c-kit/data/cases/[case_slug] before collecting records.
Do not create evidence claims from route suggestions.
```

### Licensing/professional prompt

```text
Use the $truecrime-cult-research skill and route licensing records through licensing-professional-records.
Add public license, certification, board, discipline, or sanction records for [person/org] to tc-c-kit/data/cases/[case_slug].
Distinguish lookup status, allegations, findings, and sanctions without inferring misconduct from name matches.
```

### Media/transcript prompt

```text
Use the $truecrime-cult-research skill and route media/transcript extraction through media-transcript-intelligence.
Index the transcript for [source] in tc-c-kit/data/cases/[case_slug], then extract timestamped speaker claims and source_spans.
Treat statements as claims, not established facts.
```

### Property/location prompt

```text
Use the $truecrime-cult-research skill and route property/location records through property-location-records.
Add public parcel, deed, permit, map, facility, or location records to tc-c-kit/data/cases/[case_slug].
Redact private addresses and avoid publishing exact private-person locations.
```

### Missing-persons prompt

```text
Use the $truecrime-cult-research skill and route missing-person research through missing-persons-case.
Identify source-supported missing-person or unidentified-person candidates related to [names/locations/date range] in tc-c-kit/data/cases/[case_slug].
Treat candidate matches as lead-only until identity, status, date, and location are supported by public sources.
```

### Geographical-location prompt

```text
Use the $truecrime-cult-research skill and route event/evidence geography through geographical-location-intelligence.
Map evidence-item locations, event places, routes, sightings, and locations of interest for tc-c-kit/data/cases/[case_slug].
Preserve source_spans, precision, confidence, and public/private map boundaries for every location tie.
```

### FOIA/open-records prompt

```text
Use the $truecrime-cult-research skill and route open-records planning through foia-open-records-planning.
Draft a public-records request plan for [subject] to [agency] under [jurisdiction] in tc-c-kit/data/cases/[case_slug].
Do not treat the request plan as evidence.
```

### Narrative-readiness prompt

```text
Use the $truecrime-cult-research skill and route public-output review through narrative-readiness-review.
Review tc-c-kit/data/cases/[case_slug] for source, contradiction, source-independence, privacy, and caveat blockers before script/report use.
```

### Privacy-redaction prompt

```text
Use the $truecrime-cult-research skill and route privacy review through privacy-redaction-audit.
Audit tc-c-kit/data/cases/[case_slug] for private-person, minor, address/contact, medical, financial, weak allegation, and unsupported public-export blockers.
```

### Source-independence prompt

```text
Use the $truecrime-cult-research skill and route source-chain review through source-independence-audit.
Review tc-c-kit/data/cases/[case_slug] for wire-copy, press-release repetition, same-source chains, and overstated corroboration.
```

### Source-focused prompt

```text
Use the $truecrime-cult-research skill.
For the source at [URL], ingest it into tc-c-kit/data/cases/[case_slug], extract only claims directly supported by the source, identify people/places/events/things mentioned, and create an evidence packet. Treat eyewitness statements as claims and identify whether they are firsthand or secondhand.
```

### Contradiction-check prompt

```text
Use the $truecrime-cult-research skill.
Review claims in tc-c-kit/data/cases/[case_slug]/records/claims.jsonl. Search for corrections, retractions, court findings, later interviews, and sources that contradict or narrow each claim. Update claim status/confidence and write an uncertainty report.
```

## Tooling included

The main script is:

```bash
.agents/skills/truecrime-cult-research/scripts/tcr.py
```

Important commands:

```bash
init-case
add-source
ingest-url
draft-extraction
ner-suggest
link-names
import-extraction
validate
dedupe
audit-public-export
audit-source-independence
preserve-source
resolve-identities
audit-contradictions
plan-public-records
index-transcript
plan-open-records
review-narrative-readiness
audit-privacy-redactions
report
export-manim
export-timeline
export-case-charts
export-analysis-charts
export-people-clusters
```

## Outputs intended for Manim

`export-manim` writes CSV files under:

```text
tc-c-kit/data/cases/<case_slug>/exports/manim/
```

Use these for:

- `events.csv`: timeline scenes.
- `event_links.csv`: person/event edge scenes.
- `relationships.csv`: network graph scenes.
- `claims.csv`: evidence board / claim matrix scenes.
- `people.csv`: public-safe people/entity cards.
- `places.csv`: map scenes.
- `sources.csv`: source ledger scenes.

## Final answer format when using this skill

When reporting back to the user, summarize:

1. Sources found and registered.
2. Key entities extracted.
3. Timeline/events extracted.
4. Claims by status: corroborated, single-source, disputed, excluded.
5. Privacy or legal/ethical concerns.
6. Files created or updated.
7. Next best research step.
