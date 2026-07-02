# Record Conventions

## Controlled Vocabularies

Skill-facing enum and convention values live in
`.agents/skills/truecrime-cult-research/references/controlled_vocabularies.md`.
Use schema enum values where enforced. For convention-only fields, keep the
documented values unless a case note explains a new value.

## Topic-Specific Extraction Templates

Use
`.agents/skills/truecrime-cult-research/references/topic_extraction_templates.md`
for source-packet checklists. Route domain packets to the matching adjacent
skill:

| Packet type | Skill |
|---|---|
| Corporate, organization, and financial records | `corporate-financial-records` |
| Education path records | `educational-path-records` |
| Legal and court records | `legal-court-records` |
| Entity disambiguation | `identity-resolution` |
| Capture and provenance | `source-capture-preservation` |
| Contradictions | `claim-contradiction-audit` |
| Source planning | `public-records-router` |
| Licensing records | `licensing-professional-records` |
| Media and transcripts | `media-transcript-intelligence` |
| Property and location records | `property-location-records` |
| Missing-person records | `missing-persons-case` |
| Event and evidence geography | `geographical-location-intelligence` |
| FOIA/open-records planning | `foia-open-records-planning` |
| Narrative readiness | `narrative-readiness-review` |
| Privacy and redaction | `privacy-redaction-audit` |
| Source-chain review | `source-independence-audit` |

`draft-extraction --template <template>` accepts template IDs from
`docs/registry/` (`templates` keys). The generated human index is
`.agents/skills/truecrime-cult-research/references/lane_registry.md`.

## Source Preservation Metadata

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

## Research Actions

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
`draft_extraction`, `import_extraction`, `link_names`, `preserve_source`,
`resolve_identities`, `audit_contradictions`, `plan_public_records`,
`index_transcript`, `plan_open_records`, `review_narrative_readiness`,
`audit_privacy_redactions`, `source_independence_review`, and
`audit_public_export`. Do not store source facts only in this log; facts belong
in source-backed record files.

## Citation Locators

Records that need precise citation support may reference
`records/source_spans.jsonl` rows with `source_span_ids` in addition to
`source_ids`:

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

Extraction packets may include a `source_spans` array to import span rows.
`source_span_ids` are optional on claims, events, event links, relationships,
quotes, artifacts, and redactions. They do not replace `source_ids`.

## Assertion Type

Use optional `assertion_type` to preserve how a source frames a statement:
`source_stated_fact`, `allegation`, `denial`, `court_finding`, `self_report`,
`biography_claim`, `lead_only`, or `expert_context`. This value does not
upgrade `status`, `confidence`, or public-readiness.

## Deduplication

Importers and agents should preserve stable IDs. When a duplicate is found,
keep the surviving ID, add aliases or notes, and mark the replaced retained row
`status: merged` when useful. Do not rewrite IDs already referenced by claims,
events, event links, relationships, exports, or notes.

## Source Independence

Sources may set `independence_group` to identify shared provenance, such as the
same publisher, wire story, court docket, archive packet, author, press release,
or syndication chain. Tooling falls back to publisher, URL host, then source ID
when `independence_group` is empty. Claims should be treated as corroborated
only when sources are reliable and genuinely independent.
