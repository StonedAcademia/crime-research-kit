# Research workflow

## Input

A case, group, person, place, event, or question.

## Output

A structured case workspace with:

- Sources
- Entities
- Places
- Artifacts/things
- Claims
- Events
- Event links
- Relationships
- Quotes
- Contradictions
- Privacy review notes
- Manim-ready exports

## Skill routing

Use TRCR for the case ledger and public-output guardrails. Route domain-heavy
packets to adjacent skills:

- `corporate-financial-records`: corporate, nonprofit, bank, shell-company, bankruptcy, investment, ownership, board/officer, transaction, or financial-record research.
- `educational-path-records`: schools, degrees, training, credentials, academic appointments, alumni claims, student-era events, or institution-affiliation research.
- `legal-court-records`: court dockets, filings, orders, opinions, judgments, hearings, party roles, allegations, denials, findings, or legal posture.
- `identity-resolution`: aliases, duplicate entities, ambiguous public-record identities, candidate merges, or not-same-as review.
- `source-capture-preservation`: archive URLs, capture metadata, raw/text artifacts, checksums, provenance gaps, or preservation reports.
- `claim-contradiction-audit`: corrections, retractions, denials, source conflicts, court findings, and claim-status review.
- `public-records-router`: source-lane planning across multiple public-record domains before extraction.
- `licensing-professional-records`: professional licenses, certifications, board discipline, sanctions, suspensions, revocations, or credential disputes.
- `media-transcript-intelligence`: interviews, hearings, broadcasts, podcasts, documentaries, captions, transcripts, timestamps, speakers, and quotes.
- `property-location-records`: parcels, deeds, permits, zoning, GIS/maps, facilities, campuses, public buildings, and address-sensitive location records.
- `missing-persons-case`: missing-person candidates, last-seen/time-location matching, public bulletins, status updates, and unidentified-person comparisons.
- `geographical-location-intelligence`: evidence-item geography, event maps, routes, sightings, map/exhibit locators, and locations of interest.
- `foia-open-records-planning`: public-records request scope, agency wording, exemptions, fee/appeal tracking, and released-record intake.
- `narrative-readiness-review`: public-output readiness for scripts, reports, Manim exports, bundles, and evidence boards.
- `privacy-redaction-audit`: private-person, minor, address/contact, medical, financial, weak allegation, and redaction blockers.
- `source-independence-audit`: same-source chains, wire copy, press-release repetition, and overstated corroboration.

## Workflow

1. Define the research question.
2. Create a case workspace.
3. Generate source-discovery queries.
4. Gather public-interest sources.
5. Register each source with metadata.
6. Extract source-supported entities, places, artifacts, claims, events, event links, relationships, and quotes.
7. Attach source IDs to every record.
8. Identify contradictions and missing evidence.
9. Re-score claim confidence.
10. Run privacy review.
11. Export evidence board and visualization CSVs.

## Research actions

`records/research_actions.jsonl` is an audit log. Each row should include:

- `timestamp`: UTC ISO timestamp.
- `action`: short verb phrase such as `init_case`, `ingest_url`, `import_extraction`, `link_names`, `preserve_source`, `resolve_identities`, `audit_contradictions`, `plan_public_records`, `index_transcript`, `plan_open_records`, `review_narrative_readiness`, `audit_privacy_redactions`, `audit_public_export`, or `source_independence_review`.
- `details`: object with inputs, outputs, warnings, and follow-up notes.

Use it for repeatable research steps and public-output decisions, not for source
facts. Facts belong in source-backed record files.

## Source independence

Set `independence_group` on sources when multiple items come from the same
publisher, wire story, archive packet, court docket, author, or copied source.
Tooling falls back to publisher, URL host, then source ID when
`independence_group` is empty. Treat corroboration as stronger only when the
sources are both reliable and genuinely independent.

## Deduplication

Before importing extraction packets, check existing IDs and aliases. Preserve
stable IDs, add aliases or notes, and mark retained duplicate records
`status: merged` when useful. Do not rewrite IDs already referenced by claims,
events, event links, relationships, exports, or notes.

## Public export audit

Before script, report, Manim, or public bundle output:

1. Run `validate` and fix broken references.
2. Review `privacy_review`, `privacy_level`, `living_status`, and `public_export`.
3. Treat `audit-public-export` output, when available, as the public-readiness checklist.
4. If no dedicated audit command is available, use `report`, public-safe exports, and `export-analysis-charts` public-readiness files for the same review.
5. Keep private-person details, minors, contact/location-sensitive details, weak allegations, and lead-only co-mentions out of public exports.

## Phase 1 review commands

- `preserve-source`: recompute raw/text hashes and write source-preservation metadata for an existing source.
- `resolve-identities`: write conservative identity candidate reports without merging entity rows.
- `audit-contradictions`: write contradiction review reports without changing claim status or confidence.

## Phase 2 review commands

- `plan-public-records`: write a source-lane plan for a subject without creating evidence claims.
- `index-transcript`: write timestamp and speaker-line candidate locators from a registered source text transcript.

## Phase 3 review commands

- `plan-open-records`: write a FOIA/open-records request plan without creating evidence claims.
- `review-narrative-readiness`: report public narrative blockers and caveat needs.
- `audit-privacy-redactions`: report privacy/redaction blockers before public output.
- `source-independence`: report same-source chains, wire copy, and press-release repetition.

## Additional investigation lanes

- `missing-persons-case`: route missing-person, unidentified-person, last-seen, located/recovered, and candidate-match work through a lead-first privacy review.
- `geographical-location-intelligence`: route evidence-item locations, event maps, routes, sightings, and map-ready location-of-interest packets through source-spanned geography review.

## Recommended source lanes

### News

- Local news closest to the event in time and geography.
- National news for broader reporting.
- Later retrospectives only after primary/near-contemporaneous coverage is located.

### Eyewitness accounts

Treat as claims. Capture:

- Who spoke.
- Whether they are named, anonymous, or pseudonymous.
- Whether the account is firsthand, secondhand, or unclear.
- Date of observation.
- Date of statement.
- Time gap between event and account.
- Publishing context.
- Corroborating or contradicting sources.

### Official/public records

- Court records.
- Public agency reports.
- Archive documents.
- Public hearing testimony.
- Press releases.
- Coroner/medical examiner reports only when lawful, relevant, and handled with care.

### Context

Use scholarly or expert sources to explain group dynamics, not to prove case-specific facts unless the source investigated the case directly.

## Contradiction search patterns

Search for:

```text
"<case>" correction
"<case>" retraction
"<case>" disputed
"<case>" misidentified
"<case>" lawsuit
"<case>" appeal
"<case>" overturned
"<case>" hoax
"<case>" debunked
"<person>" "not involved"
```

## Confidence scoring

Confidence is not truth. It is an internal estimate of source support.

- `0.90-1.00`: supported by primary/official or multiple independent strong sources.
- `0.70-0.89`: corroborated by multiple credible sources, but not primary.
- `0.50-0.69`: plausible but single-source or partially corroborated.
- `0.25-0.49`: weak, disputed, or based on unclear sourcing.
- `0.00-0.24`: false, retracted, contradicted, or excluded.
