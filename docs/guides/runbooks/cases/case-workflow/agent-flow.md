# Agent Flow

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

## Run The Agentic Case Builder

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

## Operating Prompts

Use these prompts as operating questions, not as evidence by themselves.

### Source Plan

```text
Use the $truecrime-cult-research skill and route source planning through public-records-router.
For data/cases/harbor_study_circle, build a source-lane plan for formation date, named public leaders, meeting locations, disputes, and corrections.
Separate official/public records, local news, national news, archive documents, transcripts/interviews, scholarly context, contradiction searches, and privacy review.
Do not create evidence claims from route suggestions.
```

### Source Preservation

```text
Use the $truecrime-cult-research skill and route source preservation through source-capture-preservation.
For data/cases/harbor_study_circle, verify source capture metadata, archive URLs, raw/text paths, checksums, and provenance gaps.
Report which sources need manual capture or stronger metadata before extraction.
```

### Single-Source Claim Review

```text
Use the $truecrime-cult-research skill.
Review claims in data/cases/harbor_study_circle/records/claims.jsonl that are single_source, unverified, disputed, or public_export: false.
For each claim, list what source support exists, what is missing, what contradiction searches to run, and whether the claim can appear in a public script.
```

### Contradiction Audit

```text
Use the $truecrime-cult-research skill and route contradiction review through claim-contradiction-audit.
Audit data/cases/harbor_study_circle for corrections, retractions, denials, court findings, later interviews, source conflicts, and date conflicts.
Do not smooth conflicts into certainty. Preserve unresolved conflicts in notes, status, confidence, and public_export.
```

### Source Independence

```text
Use the $truecrime-cult-research skill and route source-chain review through source-independence-audit.
Review data/cases/harbor_study_circle for repeated wire copy, press-release repetition, same-publisher chains, shared archive packets, and overstated corroboration.
Recommend independence_group values and identify claims that still depend on one source chain.
```

### Privacy Review

```text
Use the $truecrime-cult-research skill and route privacy review through privacy-redaction-audit.
Audit data/cases/harbor_study_circle for living private people, minors, private addresses, contact details, private workplaces/schools, medical details, family details, and weak allegations.
Return redaction blockers before any public export.
```

### Narrative Readiness

```text
Use the $truecrime-cult-research skill and route public-output review through narrative-readiness-review.
Review data/cases/harbor_study_circle for source support, contradiction handling, source independence, privacy blockers, caveat needs, and unsupported narrative points before script, report, evidence-board, or Manim use.
```
