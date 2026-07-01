# True Crime / Cult Research Skill API Spec

Status: draft v0.1  
Applies to: `.agents/skills/truecrime-cult-research`  
Primary implementation: `.agents/skills/truecrime-cult-research/scripts/tcr.py`

## Purpose

This spec defines the machine-facing API contract for the skills currently installed with this kit. Today the API is a local CLI and JSONL filesystem contract. The same operation names and payload shapes can later be wrapped by an HTTP service or MCP server without changing the case data model.

The main skill covered by this spec is `truecrime-cult-research`. Adjacent
repo-local skills such as `corporate-financial-records`,
`educational-path-records`, `legal-court-records`, `identity-resolution`,
`source-capture-preservation`, `claim-contradiction-audit`,
`public-records-router`, `licensing-professional-records`,
`media-transcript-intelligence`, `property-location-records`,
`missing-persons-case`, and `geographical-location-intelligence` extend the
same case ledger for domain-specific source packets. Phase 3 review skills
`foia-open-records-planning`, `narrative-readiness-review`,
`privacy-redaction-audit`, and `source-independence-audit` add request planning
and public-output review workflows over the same ledger.

## Safety Contract

Every operation must preserve these invariants:

- Use only public-interest and publicly available sources unless lawful user-provided material is explicitly supplied.
- Do not infer guilt, criminal responsibility, cult membership, motive, intent, or direct participation from proximity or co-mention.
- Do not label someone as suspect, perpetrator, cult member, accomplice, or person of interest unless a cited source uses that wording.
- Co-mention records created by automation must use `status: unverified`, low confidence, and `public_export: false`.
- Public exports must exclude records with `public_export: false` unless `include_private` is explicitly requested.
- Every public/video-ready claim must trace through `claim_id -> source_ids -> reliability_grade -> confidence/status -> privacy_review`.

## Data Model

Case workspaces live under:

```text
tc-c-kit/data/cases/<case_slug>/
```

Records are append-oriented JSONL files under `records/`:

| Record | File | Schema |
|---|---|---|
| Source | `records/sources.jsonl` | `docs/schemas/source.schema.json` |
| Entity | `records/entities.jsonl` | `docs/schemas/entity.schema.json` |
| Place | `records/places.jsonl` | `docs/schemas/place.schema.json` |
| Artifact | `records/artifacts.jsonl` | `docs/schemas/artifact.schema.json` |
| Claim | `records/claims.jsonl` | `docs/schemas/claim.schema.json` |
| Event | `records/events.jsonl` | `docs/schemas/event.schema.json` |
| Event link | `records/event_links.jsonl` | `docs/schemas/event_link.schema.json` |
| Relationship | `records/relationships.jsonl` | `docs/schemas/relationship.schema.json` |
| Source span | `records/source_spans.jsonl` | `docs/schemas/source_span.schema.json` |
| Quote | `records/quotes.jsonl` | `docs/schemas/quote.schema.json` |
| Redaction | `records/redactions.jsonl` | `docs/schemas/redaction.schema.json` |
| Research action | `records/research_actions.jsonl` | `docs/schemas/research_action.schema.json` |

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
| Cross-case timeline | `tc-c-kit/data/exports/timeline/*` or caller-provided `out_dir` |

## Record-Level Conventions

### Controlled vocabularies

Skill-facing enum and convention values live in
`.agents/skills/truecrime-cult-research/references/controlled_vocabularies.md`.
Use schema enum values where enforced. For convention-only fields, keep the
documented values unless a case note explains a new value.

### Topic-specific extraction templates

Use
`.agents/skills/truecrime-cult-research/references/topic_extraction_templates.md`
for source-packet checklists. Route corporate, organization, and financial
packets to `corporate-financial-records`; route education-path packets to
`educational-path-records`; route legal/court packets to
`legal-court-records`; route entity-disambiguation packets to
`identity-resolution`; route capture/provenance packets to
`source-capture-preservation`; route contradiction packets to
`claim-contradiction-audit`; route source planning to
`public-records-router`; route licensing packets to
`licensing-professional-records`; route media/transcript packets to
`media-transcript-intelligence`; route property/location packets to
`property-location-records`; route missing-person packets to
`missing-persons-case`; route event/evidence geography packets to
`geographical-location-intelligence`; route FOIA/open-records planning to
`foia-open-records-planning`; route narrative readiness to
`narrative-readiness-review`; route privacy and redaction packets to
`privacy-redaction-audit`; route source-chain review to
`source-independence-audit`.

CLI `draft-extraction --template` supports:

- `generic`
- `corporate`
- `education`
- `legal-court`
- `identity-resolution`
- `source-capture`
- `claim-contradiction`
- `public-records-router`
- `licensing-professional`
- `media-transcript`
- `property-location`
- `missing-persons`
- `geographical-location`
- `foia-open-records`
- `narrative-readiness`
- `privacy-redaction`
- `source-independence`

### Source preservation metadata

Source rows may include optional preservation fields populated by `ingest-url`
or `preserve-source`:

```json
{
  "content_type": "text/html",
  "capture_method": "ingest_url",
  "capture_timestamp": "2026-06-30T00:00:00+00:00",
  "preservation_checked_at": "2026-06-30T00:00:01+00:00",
  "raw_sha256": "hex sha-256",
  "text_sha256": "hex sha-256",
  "raw_size_bytes": 123,
  "text_size_bytes": 45,
  "preservation_status": "captured",
  "preservation_warnings": []
}
```

Allowed `capture_method` values are `ingest_url`, `manual_registration`,
`archive_lookup`, `local_file`, and `registered_source`. Allowed
`preservation_status` values are `captured`, `registered_with_archive`,
`metadata_only`, and `missing_artifacts`.

### Research actions

`records/research_actions.jsonl` records repeatable workflow steps and audit
decisions. Each row should follow this shape:

```json
{
  "timestamp": "2026-06-30T00:00:00+00:00",
  "action": "import_extraction",
  "details": {
    "inputs": [],
    "outputs": [],
    "warnings": []
  }
}
```

Use `research_actions` for operations such as `init_case`, `ingest_url`,
`draft_extraction`, `import_extraction`, `link_names`,
`preserve_source`, `resolve_identities`, `audit_contradictions`,
`plan_public_records`, `index_transcript`, `plan_open_records`,
`review_narrative_readiness`, `audit_privacy_redactions`,
`source_independence_review`, and `audit_public_export`. Do not store source
facts only in this log; facts belong in source-backed record files.

### Citation locators

Records that need precise citation support may reference rows from
`records/source_spans.jsonl` with `source_span_ids` in addition to `source_ids`:

```json
{
  "source_span_ids": ["SP..."]
}
```

The span row shape is:

```json
{
  "source_span_id": "SP...",
  "source_id": "S...",
  "locator_type": "page",
  "locator": {
    "page": 12,
    "quote_hint": "short locating phrase"
  },
  "exact_text": "Short support excerpt when needed",
  "summary": "What this span supports",
  "public_export": true,
  "notes": ""
}
```

Extraction packets may include a `source_spans` array to import these rows:

```json
{
  "source_spans": [
    {
      "source_span_id": "SP...",
      "source_id": "S...",
      "locator_type": "page",
      "locator": {
        "page": 12
      },
      "notes": ""
    }
  ]
}
```

`source_span_ids` are optional on claims, events, event links, relationships,
quotes, artifacts, and redactions. They do not replace `source_ids`.

### Assertion type

Use optional `assertion_type` to preserve how a source frames a statement:
`source_stated_fact`, `allegation`, `denial`, `court_finding`, `self_report`,
`biography_claim`, `lead_only`, or `expert_context`. This value does not
upgrade `status`, `confidence`, or public-readiness.

### Deduplication

Importers and agents should preserve stable IDs. When a duplicate is found,
keep the surviving ID, add aliases or notes, and mark the replaced retained row
`status: merged` when useful. Do not rewrite IDs already referenced by claims,
events, event links, relationships, exports, or notes.

### Source independence

Sources may set `independence_group` to identify shared provenance, such as the
same publisher, wire story, court docket, archive packet, author, press release,
or syndication chain. Tooling falls back to publisher, URL host, then source ID
when `independence_group` is empty. Claims should be treated as corroborated
only when sources are reliable and genuinely independent.

## Common Request Envelope

Use this logical envelope for programmatic callers, even when invoking the CLI:

```json
{
  "skill": "truecrime-cult-research",
  "operation": "operationName",
  "case_dir": "tc-c-kit/data/cases/<case_slug>",
  "request_id": "optional-caller-id",
  "include_private": false,
  "dry_run": false,
  "payload": {}
}
```

Common response envelope:

```json
{
  "ok": true,
  "operation": "operationName",
  "case_dir": "tc-c-kit/data/cases/<case_slug>",
  "created": [],
  "updated": [],
  "outputs": [],
  "counts": {},
  "warnings": []
}
```

Common error shape:

```json
{
  "ok": false,
  "operation": "operationName",
  "error": {
    "code": "validation_failed",
    "message": "Human-readable failure",
    "details": []
  }
}
```

Suggested error codes:

| Code | Meaning |
|---|---|
| `case_not_found` | `case.json` is missing for the requested workspace |
| `source_not_found` | Referenced `source_id` is not registered |
| `invalid_input` | Required argument or payload field is missing or malformed |
| `validation_failed` | Record validation failed |
| `privacy_blocked` | Requested public output would expose private/excluded records |
| `network_failed` | URL fetch failed |
| `schema_not_found` | A configured schema file is missing |

## Operations

### `initCase`

Creates a case workspace and empty record files.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py init-case tc-c-kit/data/cases/<case_slug> --title "<Case Title>"
```

Payload:

```json
{
  "title": "Case Title",
  "scope": "Optional research boundary",
  "public_interest": "educational/documentary research"
}
```

Creates:

- `case.json`
- `records/*.jsonl`
- `raw/`, `staging/`, `exports/`, and `notes/` directories
- `notes/case_brief.md`

### `addSource`

Registers a source without fetching content.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py add-source tc-c-kit/data/cases/<case_slug> --title "<Title>" --url "<URL>" --source-type news_article --reliability-grade B
```

Payload:

```json
{
  "title": "Source title",
  "url": "https://example.org/source",
  "source_type": "news_article",
  "reliability_grade": "B",
  "author": null,
  "publisher": null,
  "date_published": null,
  "archive_url": null,
  "independence_group": null,
  "notes": "",
  "public_export": true
}
```

Returns:

- `source_id`
- full source record

### `ingestUrl`

Fetches a public URL, extracts text where possible, and registers the source.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py ingest-url tc-c-kit/data/cases/<case_slug> "<URL>" --source-type news_article --reliability-grade B
```

Payload extends `addSource` with:

```json
{
  "url": "https://example.org/source",
  "timeout": 25
}
```

Creates:

- `raw/downloads/<safe_url>.html`
- `raw/sources/<safe_url>.txt`
- a row in `records/sources.jsonl`
- capture metadata and SHA-256 hashes for the raw and extracted text artifacts

### `draftExtraction`

Creates a source-specific extraction packet for agent or human review.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID>
```

Payload:

```json
{
  "source_id": "S...",
  "excerpt_chars": 6000,
  "template": "generic"
}
```

Creates:

- `staging/extractions/<SOURCE_ID>_extraction.json`

Packet arrays:

- `entities`
- `places`
- `artifacts`
- `claims`
- `events`
- `event_links`
- `relationships`
- `quotes`
- `redactions`

### `importExtraction`

Imports a filled extraction packet into JSONL records.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction tc-c-kit/data/cases/<case_slug> tc-c-kit/data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json
```

Payload:

```json
{
  "extraction_json": "tc-c-kit/data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json"
}
```

Behavior:

- Requires `source_id` in the packet.
- Requires the source to already exist in `records/sources.jsonl`.
- Defaults missing `source_ids` on imported rows to the packet `source_id`.
- Appends rows to their matching record files.

### `nerSuggest`

Generates crude named-entity and date candidates from registered source text.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py ner-suggest tc-c-kit/data/cases/<case_slug> --source-id <SOURCE_ID> --limit 80
```

Payload:

```json
{
  "source_id": "optional S...",
  "limit": 80
}
```

Creates:

- `staging/candidates/ner_suggestions_<date>.json`

Notes:

- Output is lead-only and must not be treated as evidence.

### `linkNames`

Links a caller-provided name list to existing events and co-mentions.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py link-names tc-c-kit/data/cases/<case_slug> --names-file names.txt --name "Primary Name|Alias"
```

Payload:

```json
{
  "names": [
    "Primary Name|Alias One|Alias Two"
  ],
  "names_file": "optional path"
}
```

Behavior:

- Resolves names against entity `name`, `display_name`, and `aliases`.
- Merges overlapping aliases before creating candidates.
- Creates unmatched names as candidate person entities.
- Refreshes candidate/entity `source_ids` on rerun when new source text matches.
- Writes `co_mentioned_in_event` event links and `co_mentioned_with` relationships only as private, unverified research leads.
- Writes a research brief under `notes/name_link_research_<date>_<names>.md`.

Safety defaults:

```json
{
  "relation_type": "co_mentioned_in_event | co_mentioned_with",
  "status": "unverified",
  "public_export": false,
  "confidence": "low"
}
```

### `validateCase`

Validates case records against required fields and available schemas.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate tc-c-kit/data/cases/<case_slug>
```

Payload:

```json
{}
```

Returns:

- success message, or
- validation errors by record type and row index

### `reportCase`

Writes a Markdown evidence board.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py report tc-c-kit/data/cases/<case_slug>
```

Creates:

- `exports/evidence_board.md`

Includes:

- source ledger
- entities
- events
- event links
- relationships
- claims by status
- redactions/public-output exclusions

### `exportManim`

Exports public-safe Manim-ready CSVs.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-manim tc-c-kit/data/cases/<case_slug>
```

Payload:

```json
{
  "include_private": false
}
```

Creates:

- `exports/manim/sources.csv`
- `exports/manim/people.csv`
- `exports/manim/places.csv`
- `exports/manim/claims.csv`
- `exports/manim/events.csv`
- `exports/manim/event_links.csv`
- `exports/manim/relationships.csv`

### `auditPublicExport`

Audits whether a case is ready for public/script/video/export use.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-public-export tc-c-kit/data/cases/<case_slug>
```

Payload:

```json
{
  "include_private": false,
  "warn_only": false,
  "out": null
}
```

Checklist:

- Broken references or invalid rows fail the audit.
- `privacy_review: needs_review`, `redact`, or `exclude` blocks public use until resolved.
- Living private people, minors, private contact/location details, medical details, weak allegations, and lead-only co-mentions must stay `public_export: false`.
- Claims with `status: disputed`, `unverified`, `false_or_retracted`, or `excluded_from_public_script` need explicit public-facing caveats or exclusion.
- Rows created from `lead_only`, `co_mentioned_in_event`, or `co_mentioned_with` are not public-ready without source-stated support.

Expected outputs:

- a `research_actions` row with `action: audit_public_export`
- warnings grouped by record type and record ID
- JSON audit artifact under `exports/public_export_audit.json` or caller-provided `--out`

### `dedupeRecords`

Reports conservative duplicate candidates for entities, sources, and claims.
The command does not merge or delete evidence rows.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py dedupe tc-c-kit/data/cases/<case_slug>
```

Payload:

```json
{
  "record_type": "all",
  "min_key_chars": 12,
  "out": null
}
```

Expected outputs:

- JSON candidate report under `staging/candidates/dedupe_report_<date>.json` or caller-provided `--out`
- a `research_actions` row with `action: dedupe`

### `preserveSource`

Computes preservation metadata for an existing source and writes a JSON
preservation report. This operation updates only the source row's preservation
metadata and does not create claims, entities, events, or relationships.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py preserve-source tc-c-kit/data/cases/<case_slug> <SOURCE_ID>
```

Payload:

```json
{
  "source_id": "S...",
  "archive_url": null,
  "content_type": null,
  "out": null
}
```

Expected outputs:

- updated optional preservation fields on the matching source row
- JSON report under `exports/source_preservation/<SOURCE_ID>.json` or caller-provided `--out`
- a `research_actions` row with `action: preserve_source`

### `resolveIdentities`

Reports conservative identity-resolution candidates for entities with matching
names or aliases. The command does not merge, delete, or publicly identify
records.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py resolve-identities tc-c-kit/data/cases/<case_slug>
```

Payload:

```json
{
  "min_key_chars": 8,
  "include_merged": false,
  "out": null
}
```

Expected outputs:

- JSON candidate report under `staging/candidates/identity_resolution_<date>.json` or caller-provided `--out`
- a `research_actions` row with `action: resolve_identities`

### `auditContradictions`

Reports explicit and likely claim contradictions. This command identifies review
targets and does not change claim status, confidence, or public-export flags.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-contradictions tc-c-kit/data/cases/<case_slug>
```

Payload:

```json
{
  "include_private": false,
  "min_overlap": 0.45,
  "fail_on_flags": false,
  "out": null
}
```

Expected outputs:

- JSON report under `exports/claim_contradiction_audit.json` or caller-provided `--out`
- a `research_actions` row with `action: audit_contradictions`

### `planPublicRecords`

Writes a source-lane plan for a subject. This is a planning artifact only; it
does not create evidence claims or imply misconduct, identity, or relationships.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py plan-public-records tc-c-kit/data/cases/<case_slug> --subject "<subject>"
```

Payload:

```json
{
  "subject": "Person, organization, place, event, or question",
  "question": "",
  "lane": [],
  "out": null
}
```

Supported `lane` values are `legal-court`, `corporate`, `education`,
`licensing-professional`, `media-transcript`, `property-location`,
`missing-persons`, `geographical-location`, `source-capture`,
`identity-resolution`, and `contradiction`.

Expected outputs:

- JSON source plan under `staging/candidates/public_records_plan_<subject>_<date>.json` or caller-provided `--out`
- a `research_actions` row with `action: plan_public_records`

### `indexTranscript`

Indexes timestamp and speaker-line candidates from an already registered source
text file. This report helps create source spans and quotes but does not import
claims or quotes.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py index-transcript tc-c-kit/data/cases/<case_slug> <SOURCE_ID>
```

Payload:

```json
{
  "source_id": "S...",
  "max_segments": 200,
  "include_private": false,
  "out": null
}
```

Expected outputs:

- JSON transcript index under `staging/candidates/transcript_index_<source_id>_<date>.json` or caller-provided `--out`
- a `research_actions` row with `action: index_transcript`

### `planOpenRecords`

Writes a FOIA/open-records request plan. This is a planning artifact and does
not prove that records exist.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py plan-open-records tc-c-kit/data/cases/<case_slug> --subject "<subject>" --agency "<agency>"
```

Payload:

```json
{
  "subject": "Request subject",
  "agency": "Agency or public body",
  "jurisdiction": null,
  "law": null,
  "date_range": null,
  "record": [],
  "out": null
}
```

Expected outputs:

- JSON request plan under `staging/candidates/open_records_plan_<subject>_<date>.json` or caller-provided `--out`
- a `research_actions` row with `action: plan_open_records`

### `reviewNarrativeReadiness`

Reports blockers and caveats before public narrative use. This command does not
rewrite claims, events, relationships, or public-export flags.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py review-narrative-readiness tc-c-kit/data/cases/<case_slug>
```

Payload:

```json
{
  "include_private": false,
  "require_spans": false,
  "min_independent_sources": 2,
  "fail_on_blockers": false,
  "out": null
}
```

Expected outputs:

- JSON readiness report under `exports/narrative_readiness_review.json` or caller-provided `--out`
- a `research_actions` row with `action: review_narrative_readiness`

### `auditPrivacyRedactions`

Reports privacy and redaction blockers before public output.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-privacy-redactions tc-c-kit/data/cases/<case_slug>
```

Payload:

```json
{
  "include_private": false,
  "require_redaction_log": false,
  "warn_only": false,
  "out": null
}
```

Expected outputs:

- JSON audit report under `exports/privacy_redaction_audit.json` or caller-provided `--out`
- a `research_actions` row with `action: audit_privacy_redactions`

### `auditSourceIndependence`

Reports repeated wire copy, press-release repetition, and same-source-chain
support risks. The `source-independence` alias is equivalent to
`audit-source-independence`.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py source-independence tc-c-kit/data/cases/<case_slug>
```

Payload:

```json
{
  "include_private": false,
  "min_title_chars": 16,
  "fail_on_flags": false,
  "out": null
}
```

Expected outputs:

- JSON report under `exports/source_independence_report.json` or caller-provided `--out`
- a `research_actions` row with `action: audit_source_independence`

### `exportTimeline`

Exports a cross-case timeline and claim corroboration index.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-timeline tc-c-kit/data/cases
```

Payload:

```json
{
  "cases_root": "tc-c-kit/data/cases",
  "out_dir": null,
  "include_private": false
}
```

Creates:

- `cases.csv`
- `timeline.csv`
- `corroborations.csv`
- `timeline.md`

Default output:

```text
tc-c-kit/data/exports/timeline/
```

### `exportCaseCharts`

Exports case-level chart artifacts for people graph and subcase timeline review.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-case-charts tc-c-kit/data/cases/<case_slug>
```

Payload:

```json
{
  "out_dir": null,
  "include_private": false
}
```

Creates:

- `people_graph.html`
- `people_nodes.csv`
- `people_edges.csv`
- `subcase_timelines.html`
- `subcase_timelines.csv`
- `subcase_summary.csv`

Default output:

```text
tc-c-kit/data/cases/<case_slug>/exports/charts/
```

### `exportAnalysisCharts`

Exports public-readiness, source-quality, corroboration, path, and relationship
analysis artifacts. This is the main source-independence tooling surface.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-analysis-charts tc-c-kit/data/cases/<case_slug> --include-private
```

Payload:

```json
{
  "out_dir": null,
  "clusters_dir": null,
  "include_private": true
}
```

Creates:

- `analysis_charts.html`
- `analysis_charts.md`
- `cluster_bridge_sankey.csv`
- `cluster_bridge_sankey_nodes.csv`
- `cluster_bridge_sankey_links.csv`
- `layered_knowledge_graph_nodes.csv`
- `layered_knowledge_graph_edges.csv`
- `layered_knowledge_graph_v2_nodes.csv`
- `layered_knowledge_graph_v2_edges.csv`
- `layered_knowledge_graph_v2_layers.csv`
- `bridge_fragility.csv`
- `bridge_fragility_segments.csv`
- `claim_corroboration_matrix.csv`
- `claim_corroboration_edges.csv`
- `source_quality_dashboard.csv`
- `evidence_confidence_heatmap.csv`
- `evidence_confidence_heatmap_aggregate.csv`
- `contradiction_boundary_overlay.csv`
- `temporal_cluster_swimlanes.csv`
- `public_narrative_readiness.csv`
- `relationship_type_treemap.csv`
- `person_source_bipartite.csv`
- `person_source_bipartite_nodes.csv`
- `person_source_bipartite_edges.csv`
- `sixdof_path_atlas.csv`
- `sixdof_path_segments.csv`

Use `source_quality_dashboard.csv` and `claim_corroboration_matrix.csv` to
check reliability grades, source counts, independent source counts, and
public-readiness before upgrading claims or exporting public scripts.

### `exportPeopleClusters`

Runs evidence-weighted Leiden clustering and graph-kernel/KDE density analysis
over the people graph.

CLI:

```bash
uv run --extra dev --with igraph --with leidenalg \
  python .agents/skills/truecrime-cult-research/scripts/tcr.py export-people-clusters tc-c-kit/data/cases/<case_slug> --include-private
```

Payload:

```json
{
  "out_dir": null,
  "charts_dir": null,
  "include_private": true,
  "resolution": 1.0,
  "seed": 7,
  "sigma": null
}
```

Creates:

- `people_clusters.html`
- `people_clusters.csv`
- `cluster_summary.csv`
- `people_cluster_edges.csv`
- `people_kernel_matrix.csv`
- `clusters.md`

Default output:

```text
tc-c-kit/data/cases/<case_slug>/exports/clusters/
```

## Future HTTP Mapping

If this CLI is wrapped by an HTTP API, use these stable operation routes:

| Method | Path | Operation |
|---|---|---|
| `POST` | `/v1/cases` | `initCase` |
| `POST` | `/v1/cases/{case_slug}/sources` | `addSource` |
| `POST` | `/v1/cases/{case_slug}/sources:ingest-url` | `ingestUrl` |
| `POST` | `/v1/cases/{case_slug}/extractions:draft` | `draftExtraction` |
| `POST` | `/v1/cases/{case_slug}/extractions:import` | `importExtraction` |
| `POST` | `/v1/cases/{case_slug}/candidates:ner-suggest` | `nerSuggest` |
| `POST` | `/v1/cases/{case_slug}/links:names` | `linkNames` |
| `POST` | `/v1/cases/{case_slug}:validate` | `validateCase` |
| `POST` | `/v1/cases/{case_slug}:report` | `reportCase` |
| `POST` | `/v1/cases/{case_slug}/exports:manim` | `exportManim` |
| `POST` | `/v1/cases/{case_slug}:dedupe` | `dedupeRecords` |
| `POST` | `/v1/cases/{case_slug}:audit-public-export` | `auditPublicExport` |
| `POST` | `/v1/cases/{case_slug}:audit-source-independence` | `auditSourceIndependence` |
| `POST` | `/v1/cases:export-timeline` | `exportTimeline` |
| `POST` | `/v1/cases/{case_slug}/exports:charts` | `exportCaseCharts` |
| `POST` | `/v1/cases/{case_slug}/exports:analysis-charts` | `exportAnalysisCharts` |
| `POST` | `/v1/cases/{case_slug}/exports:people-clusters` | `exportPeopleClusters` |

The HTTP wrapper must preserve local safety defaults, especially explicit opt-in for private records.

## Versioning

Use semantic versions for the skill API contract:

- `0.x`: draft/local-only; breaking changes allowed with docs updates.
- `1.0`: stable record schemas, stable operation names, and stable response envelope.

Breaking changes include:

- renaming operation names
- removing request fields
- changing default privacy/public-export behavior
- changing CSV column names
- changing record ID generation semantics

Non-breaking changes include:

- adding optional request fields
- adding new output files
- adding new record fields under schemas that allow additional properties
- adding new validation warnings

## Open Questions

- Whether `review-links` should become a first-class operation for promoting, excluding, or annotating co-mention links.
- Whether stronger source-stated relationship upgrades should be handled by `importExtraction` options or a separate review operation.
- Whether future service wrappers should expose raw source text or keep it local-only.
