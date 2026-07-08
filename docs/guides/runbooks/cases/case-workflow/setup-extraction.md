# Case Setup And Extraction

## Case Workspace Layout

Generated case work stays under `data/cases/`, which is ignored by Git except
for `data/cases/.gitkeep`. Keep reusable fixtures in `data/examples/`.

```text
data/cases/<case_slug>/
  case.json
  raw/
    downloads/
    sources/
  records/
    sources.jsonl
    entities.jsonl
    places.jsonl
    artifacts.jsonl
    claims.jsonl
    events.jsonl
    event_links.jsonl
    relationships.jsonl
    quotes.jsonl
    research_actions.jsonl
    redactions.jsonl
  staging/
    extractions/
    candidates/
  exports/
    evidence_board.md
    internal/
```

## Example Case

Use a fictional public-source case for practice:

```text
Case title: Harbor Study Circle Source Map
Case slug: harbor_study_circle
Research question: What can public sources establish about the group's
formation, named public leaders, meeting locations, documented disputes, and
later public corrections?
Boundary: Do not identify private relatives, minors, private addresses,
private workplaces, or living private people unless a source-supported public
interest reason is recorded.
```

Initialize the workspace:

```bash
crk-ledger init-case data/cases/harbor_study_circle \
  --title "Harbor Study Circle Source Map"
```

## Ask The Agent To Start Correctly

Use a prompt that names the skill, scope, source standard, and public-output
boundary:

```text
Use the $truecrime-cult-research skill.
Create or open data/cases/harbor_study_circle for the synthetic Harbor Study Circle example.
Build a public-source plan for the group's formation, named public leaders, meeting locations, documented disputes, and later corrections.
Use public news, official records, archive documents, interviews/transcripts, and scholarly context.
Do not infer guilt, motive, membership, or hidden control from proximity.
Do not publish private-person details, private addresses, minors, contact details, medical details, or weak allegations.
Return the source lanes, the first sources to register, and the review gates before extraction.
```

Expected first output:

- Source lanes: local news, national news, official/public records, archives,
  interviews/transcripts, contradictions, source independence, privacy review.
- Candidate source list with source type and reliability grade.
- No claims treated as established before sources are registered.
- A plan for which adjacent skills should handle specialized packets.

Write source plans before treating route suggestions as evidence:

```bash
crk-ledger plan-public-records data/cases/harbor_study_circle \
  --subject "Harbor Study Circle"
crk-ledger plan-open-records data/cases/harbor_study_circle \
  --agency "Harbor City Council" \
  --subject "Harbor Study Circle"
```

## Use Agent Flows By Lane

| Research need | Ask for this skill or flow | Expected output |
|---|---|---|
| General case ledger and safety baseline | `truecrime-cult-research` | Case workspace, source list, extraction packets, claims, events, relationships, exports. |
| Court records, filings, orders, judgments | `legal-court-records` | Allegations, denials, findings, docket metadata, source spans. |
| Corporate, nonprofit, board, financial records | `corporate-financial-records` | Source-stated entities, officers, filings, transactions, relationship claims. |
| Transcripts, interviews, podcasts, hearings | `media-transcript-intelligence` | Timestamped speaker claims, quotes, transcript locators. |
| Public-record source planning | `public-records-router` | Source-lane plan only, not evidence claims. |
| FOIA or open-records planning | `foia-open-records-planning` | Request wording, agency targets, exemptions, tracking plan. |
| Ambiguous names or aliases | `identity-resolution` | Candidate same-as/not-same-as notes without automatic merges. |
| Source preservation and hashes | `source-capture-preservation` | Archive URLs, raw/text paths, checksums, provenance gaps. |
| Corrections, denials, conflicting accounts | `claim-contradiction-audit` | Claim conflict report and status recommendations. |
| Same-source chains and repeated wire copy | `source-independence-audit` | Independence groups and corroboration warnings. |
| Privacy and redactions | `privacy-redaction-audit` | Private-person, minor, address, contact, medical, financial, and weak-allegation blockers. |
| Public scripts, reports, visual output, evidence boards | `narrative-readiness-review` | Readiness blockers, caveats, unsupported narrative points. |

## Register Sources Before Extracting Claims

For a downloadable public URL:

```bash
crk-ledger ingest-url data/cases/harbor_study_circle \
  "https://example.com/harbor-local-report-1978" \
  --source-type news_article \
  --reliability-grade B
```

For a source that needs manual registration:

```bash
crk-ledger add-source data/cases/harbor_study_circle \
  --title "Harbor City Council Meeting Minutes, May 1978" \
  --url "https://example.com/harbor-council-minutes-1978" \
  --source-type government_record \
  --reliability-grade A \
  --notes "Synthetic example; manual registration before packet extraction"
```

Ask Codex to keep the source ledger conservative:

```text
For each source in data/cases/harbor_study_circle/records/sources.jsonl, check whether title, URL/path, publication metadata, source_type, reliability_grade, archive/preservation notes, and independence_group are present.
Do not extract claims yet. Report missing metadata and suggest source IDs that need preservation or manual review.
```

Preserve local source files and hashes before extraction when the source is not
already archived:

```bash
crk-ledger preserve-source data/cases/harbor_study_circle <SOURCE_ID>
```

## Draft And Fill Extraction Packets

Draft a generic packet:

```bash
crk-ledger draft-extraction data/cases/harbor_study_circle <SOURCE_ID>
```

Draft a lane-specific packet when the source calls for it:

```bash
crk-ledger draft-extraction data/cases/harbor_study_circle <SOURCE_ID> \
  --template media-transcript
```

Ask the agent to fill only what the source supports:

```text
Use the $truecrime-cult-research skill.
Fill data/cases/harbor_study_circle/staging/extractions/<SOURCE_ID>_extraction.json from the registered source text.
Extract only source-stated entities, places, artifacts, claims, events, event_links, relationships, quotes, and source_spans.
Use neutral wording and preserve assertion framing.
Treat eyewitness statements as claims, not facts.
Set weak, single-source, private-person, or lead-only rows to public_export: false when appropriate.
Do not add facts from memory or summaries that are not in the source.
```

Review staged packets for `source_ids`, `source_span_ids`, privacy defaults,
assertion framing, and conservative status/confidence before importing.

```bash
crk-ledger import-extraction data/cases/harbor_study_circle \
  data/cases/harbor_study_circle/staging/extractions/<SOURCE_ID>_extraction.json
```

Use local suggestions only as review aids, not as canonical records:

```bash
crk-ledger ner-suggest data/cases/harbor_study_circle <SOURCE_ID>
crk-ledger index-transcript data/cases/harbor_study_circle <SOURCE_ID>
```
