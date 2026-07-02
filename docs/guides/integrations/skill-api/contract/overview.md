# Skill API Overview

This contract defines the machine-facing surface for the skills installed with
the kit. Today the API is a local CLI and JSONL filesystem contract. The same
operation names and payload shapes can later be wrapped by an HTTP service or
MCP server without changing the case data model.

## Safety Contract

Every operation must preserve these invariants:

- Use only public-interest and publicly available sources unless lawful user-provided material is explicitly supplied.
- Do not infer guilt, criminal responsibility, cult membership, motive, intent, or direct participation from proximity or co-mention.
- Do not label someone as suspect, perpetrator, cult member, accomplice, or person of interest unless a cited source uses that wording.
- Co-mention records created by automation must use `status: unverified`, low confidence, and `public_export: false`.
- Public exports must exclude records with `public_export: false` unless `include_private` is explicitly requested.
- Every public-facing claim must trace through `claim_id -> source_ids -> reliability_grade -> confidence/status -> privacy_review`.

## Case Workspace

Case workspaces live under:

```text
data/cases/<case_slug>/
```

Records are append-oriented JSONL files under `records/`:

| Record | File | Schema |
|---|---|---|
| Source | `records/sources.jsonl` | `docs/schemas/case/source.schema.json` |
| Entity | `records/entities.jsonl` | `docs/schemas/case/entity.schema.json` |
| Place | `records/places.jsonl` | `docs/schemas/case/place.schema.json` |
| Artifact | `records/artifacts.jsonl` | `docs/schemas/case/artifact.schema.json` |
| Claim | `records/claims.jsonl` | `docs/schemas/evidence/claim.schema.json` |
| Event | `records/events.jsonl` | `docs/schemas/evidence/event.schema.json` |
| Event link | `records/event_links.jsonl` | `docs/schemas/evidence/event_link.schema.json` |
| Relationship | `records/relationships.jsonl` | `docs/schemas/evidence/relationship.schema.json` |
| Source span | `records/source_spans.jsonl` | `docs/schemas/review/source_span.schema.json` |
| Quote | `records/quotes.jsonl` | `docs/schemas/review/quote.schema.json` |
| Redaction | `records/redactions.jsonl` | `docs/schemas/review/redaction.schema.json` |
| Research action | `records/research_actions.jsonl` | `docs/schemas/review/research_action.schema.json` |

Generated files are written under:

| Output | Path |
|---|---|
| Source text | `raw/sources/*.txt` |
| Raw downloads | `raw/downloads/*` |
| Extraction packets | `staging/extractions/*.json` |
| Candidate suggestions | `staging/candidates/*.json` |
| Identity resolution reports | `staging/candidates/identity_resolution_<date>.json` |
| Public-record source plans | `staging/candidates/public_records_plan_<subject>_<date>.json` |
| Transcript index reports | `staging/candidates/transcript_index_<source_id>_<date>.json` |
| Open-records request plans | `staging/candidates/open_records_plan_<subject>_<date>.json` |
| Evidence board | `exports/evidence_board.md` |
| Source preservation reports | `exports/source_preservation/*.json` |
| Claim contradiction audit | `exports/claim_contradiction_audit.json` |
| Narrative readiness review | `exports/narrative_readiness_review.json` |
| Privacy redaction audit | `exports/privacy_redaction_audit.json` |
| Manim CSVs | `exports/manim/*.csv` |
| Case charts | `exports/charts/*` |
| Cross-case timeline | `data/exports/timeline/*` or caller-provided `out_dir` |
