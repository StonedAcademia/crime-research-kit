# Case Workflow Runbook

This runbook shows how to ask Codex or another agent to use the TRCR skills and
agent flows without turning lead discovery into unsourced claims. The example is
synthetic and uses placeholder sources.

Commands assume they are run from the `tc-c-kit` repository root so the skill
script path is `.agents/skills/truecrime-cult-research/scripts/tcr.py` and case
work stays under `data/cases/`.

## Working Rule

Every public-facing point must reduce to:

```text
claim -> source_ids -> reliability grade -> confidence/status -> privacy review -> export
```

If that chain is incomplete, keep the point out of public scripts, evidence
boards, Manim exports, and public bundles except as an explicitly unknown,
lead-only, or disputed item.

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
    manim/
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
python .agents/skills/truecrime-cult-research/scripts/tcr.py init-case data/cases/harbor_study_circle \
  --title "Harbor Study Circle Source Map"
```

## Ask the Agent to Start Correctly

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

## Use Agent Flows by Lane

| Research need | Ask for this skill or flow | Expected output |
| --- | --- | --- |
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
| Public scripts, reports, Manim output, evidence boards | `narrative-readiness-review` | Readiness blockers, caveats, unsupported narrative points. |

## Register Sources Before Extracting Claims

For a downloadable public URL:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py ingest-url data/cases/harbor_study_circle \
  "https://example.com/harbor-local-report-1978" \
  --source-type news_article \
  --reliability-grade B
```

For a source that needs manual registration:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py add-source data/cases/harbor_study_circle \
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

## Draft and Fill Extraction Packets

Draft a generic packet:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction data/cases/harbor_study_circle <SOURCE_ID>
```

Draft a lane-specific packet when the source calls for it:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction data/cases/harbor_study_circle <SOURCE_ID> \
  --template media-transcript
```

Ask the agent to fill only what the source supports:

```text
Use the $truecrime-cult-research skill.
Fill data/cases/harbor_study_circle/staging/extractions/<SOURCE_ID>_extraction.json from the registered source text.
Extract only source-stated entities, places, artifacts, claims, events, event_links, relationships, quotes, and source_spans.
Use neutral wording and preserve whether each assertion is a source-stated fact, allegation, denial, court finding, self-report, lead-only item, or expert context.
Treat eyewitness statements as claims, not facts.
Set weak, single-source, private-person, or lead-only rows to public_export: false when appropriate.
Do not add facts from memory or summaries that are not in the source.
```

Review the staged packet before importing. The human review should check:

- Does every claim, event, quote, relationship, or event link have `source_ids`?
- Do precise or contested points have `source_span_ids`?
- Are living private people, minors, addresses, contact details, and medical or
  family details private by default?
- Does the packet distinguish allegations, denials, findings, eyewitness
  accounts, expert context, and lead-only items?
- Are confidence and status values conservative?

Import only after review:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction data/cases/harbor_study_circle \
  data/cases/harbor_study_circle/staging/extractions/<SOURCE_ID>_extraction.json
```

## Link Names Conservatively

Use `link-names` when you need candidate event and co-mention links for known
names or aliases:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py link-names data/cases/<case_slug> \
  --names-file names.txt \
  --name "Primary Name|Known Alias"
```

`link-names` writes conservative, private-by-default co-mention records and a
research brief under `notes/`. It does not make guilt, membership, motive, or
participation claims from proximity.

## Run the Agentic Case Builder

Use the app for a planned, resumable workflow around the same ledger:

```bash
trcr-case-builder plan data/cases/harbor_study_circle \
  --title "Harbor Study Circle Source Map" \
  --subject "formation, public leaders, meeting locations, disputes, corrections" \
  --source-url "https://example.com/harbor-local-report-1978" \
  --runner langgraph \
  --checkpoint \
  --execute
```

The flow is:

```text
infer_lanes -> suggest_lanes -> init_case -> plan_public_records
  -> source_capture -> parse_or_ocr -> draft_packets
  -> fill_packets -> packet_review_gate
  -> import_and_validate -> index_case -> readiness_audit
  -> readiness_brief -> export_review_gate -> export_bundle
```

The packet review gate exists so an agent cannot silently promote a draft into
canonical records. Resume with approvals after packet review:

```bash
trcr-case-builder resume data/cases/harbor_study_circle \
  --thread <thread_id> \
  --approve-packet <SOURCE_ID>_extraction.json \
  --execute
```

Resume with public-export approval only after validation, contradiction review,
source-independence review, and privacy review:

```bash
trcr-case-builder resume data/cases/harbor_study_circle \
  --thread <thread_id> \
  --approve-export \
  --execute
```

## Questions Worth Asking During the Case

Use these prompts as operating questions, not as evidence by themselves.

### Source plan

```text
Use the $truecrime-cult-research skill and route source planning through public-records-router.
For data/cases/harbor_study_circle, build a source-lane plan for formation date, named public leaders, meeting locations, disputes, and corrections.
Separate official/public records, local news, national news, archive documents, transcripts/interviews, scholarly context, contradiction searches, and privacy review.
Do not create evidence claims from route suggestions.
```

### Source preservation

```text
Use the $truecrime-cult-research skill and route source preservation through source-capture-preservation.
For data/cases/harbor_study_circle, verify source capture metadata, archive URLs, raw/text paths, checksums, and provenance gaps.
Report which sources need manual capture or stronger metadata before extraction.
```

### Single-source claim review

```text
Use the $truecrime-cult-research skill.
Review claims in data/cases/harbor_study_circle/records/claims.jsonl that are single_source, unverified, disputed, or public_export: false.
For each claim, list what source support exists, what is missing, what contradiction searches to run, and whether the claim can appear in a public script.
```

### Contradiction audit

```text
Use the $truecrime-cult-research skill and route contradiction review through claim-contradiction-audit.
Audit data/cases/harbor_study_circle for corrections, retractions, denials, court findings, later interviews, source conflicts, and date conflicts.
Do not smooth conflicts into certainty. Preserve unresolved conflicts in notes, status, confidence, and public_export.
```

### Source independence

```text
Use the $truecrime-cult-research skill and route source-chain review through source-independence-audit.
Review data/cases/harbor_study_circle for repeated wire copy, press-release repetition, same-publisher chains, shared archive packets, and overstated corroboration.
Recommend independence_group values and identify claims that still depend on one source chain.
```

### Privacy review

```text
Use the $truecrime-cult-research skill and route privacy review through privacy-redaction-audit.
Audit data/cases/harbor_study_circle for living private people, minors, private addresses, contact details, private workplaces/schools, medical details, family details, and weak allegations.
Return redaction blockers before any public export.
```

### Narrative readiness

```text
Use the $truecrime-cult-research skill and route public-output review through narrative-readiness-review.
Review data/cases/harbor_study_circle for source support, contradiction handling, source independence, privacy blockers, caveat needs, and unsupported narrative points before script, report, evidence-board, or Manim use.
```

## Validate and Export

Validate the ledger:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate data/cases/harbor_study_circle
python .agents/skills/truecrime-cult-research/scripts/tcr.py report data/cases/harbor_study_circle
```

Run public-output audits:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-public-export data/cases/harbor_study_circle
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-privacy-redactions data/cases/harbor_study_circle
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-source-independence data/cases/harbor_study_circle
python .agents/skills/truecrime-cult-research/scripts/tcr.py review-narrative-readiness data/cases/harbor_study_circle
```

Export Manim-ready CSVs after review:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-manim data/cases/harbor_study_circle
```

Export a public-safe Phanestead bundle:

```bash
bun deployment/scripts/export_trcr_ufb.mjs data/cases/harbor_study_circle \
  --out data/cases/harbor_study_circle/exports/ufb/harbor_study_circle.ufb_v2
```

Use `--include-private` only for internal review artifacts.

## Good Case Questions

Ask questions that preserve source boundaries:

- What does each source directly state, and which source ID supports it?
- Is this claim a source-stated fact, allegation, denial, court finding,
  self-report, lead-only item, or expert context?
- Is this source independent, or does it repeat another source chain?
- What corrections, denials, retractions, lawsuits, appeals, or later public
  records narrow this claim?
- Does this record include a living private person, minor, address, contact
  detail, medical detail, private family detail, or weak allegation?
- Which claims are safe for a public script, which are internal only, and which
  should be excluded?
- Which timeline events lack precise source spans?
- Which relationships are source-stated, and which are merely co-mentions or
  hypotheses?
- What would change the confidence score?
- What is still unknown or not established?

Avoid questions that force unsupported conclusions:

- Who is obviously guilty?
- Which private people should be exposed?
- Can we infer membership from attendance or proximity?
- Can the agent fill gaps from memory?
- Can repeated copies of the same article count as corroboration?
- Can a route suggestion become an evidence claim?

## Done Criteria

A case pass is ready for public-output review when:

1. Source rows include URL/path, publication metadata, source type,
   reliability grade, and preservation notes where available.
2. Entities, places, artifacts, claims, events, event links, relationships,
   quotes, source spans, and redactions use stable IDs.
3. Every claim has source IDs, status, confidence, and public-export handling.
4. Contradictions, corrections, denials, and missing evidence are recorded.
5. Source independence has been reviewed before marking claims corroborated.
6. Privacy and redaction blockers are resolved or kept internal.
7. `validate` passes.
8. The evidence board, Manim CSVs, charts, or bundle exports are generated only
   from public-safe rows unless internal review explicitly uses
   `--include-private`.
