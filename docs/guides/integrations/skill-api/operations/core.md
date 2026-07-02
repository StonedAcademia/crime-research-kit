# Core Skill Operations

## Common Request Envelope

Programmatic callers should use this logical envelope even when invoking the CLI:

```json
{
  "skill": "truecrime-cult-research",
  "operation": "operationName",
  "case_dir": "data/cases/<case_slug>",
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
  "case_dir": "data/cases/<case_slug>",
  "created": [],
  "updated": [],
  "outputs": [],
  "counts": {},
  "warnings": []
}
```

Common error codes include `case_not_found`, `source_not_found`,
`invalid_input`, `validation_failed`, `privacy_blocked`, `network_failed`, and
`schema_not_found`.

## `initCase`

Creates a case workspace and empty record files.

CLI:

```bash
crk-ledger init-case data/cases/<case_slug> --title "<Case Title>"
```

Payload: `title`, optional `scope`, and `public_interest`. Creates `case.json`,
empty `records/*.jsonl`, `raw/`, `staging/`, `exports/`, `notes/`, and
`notes/case_brief.md`.

## `addSource`

Registers a source without fetching content.

CLI:

```bash
crk-ledger add-source data/cases/<case_slug> --title "<Title>" --url "<URL>" --source-type news_article --reliability-grade B
```

Payload fields: `title`, `url`, `source_type`, `reliability_grade`, optional
`author`, `publisher`, `date_published`, `archive_url`, `independence_group`,
`notes`, and `public_export`. Returns the generated `source_id` and source row.

## `ingestUrl`

Fetches a public URL, extracts text where possible, and registers the source.

CLI:

```bash
crk-ledger ingest-url data/cases/<case_slug> "<URL>" --source-type news_article --reliability-grade B
```

Payload extends `addSource` with `timeout`. Creates raw download text,
extracted source text, a source row, capture metadata, and SHA-256 hashes.

## `draftExtraction`

Creates a source-specific extraction packet for agent or human review.

CLI:

```bash
crk-ledger draft-extraction data/cases/<case_slug> <SOURCE_ID>
```

Payload fields: `source_id`, `excerpt_chars`, and `template`. Creates
`staging/extractions/<SOURCE_ID>_extraction.json` with arrays for entities,
places, artifacts, claims, events, event links, relationships, quotes, and
redactions.

## `importExtraction`

Imports a filled extraction packet into JSONL records.

CLI:

```bash
crk-ledger import-extraction data/cases/<case_slug> data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json
```

Payload field: `extraction_json`. The packet must include `source_id`, and the
source must already exist in `records/sources.jsonl`. Missing row
`source_ids` default to the packet source before rows are appended.

## `nerSuggest`

Generates crude named-entity and date candidates from registered source text.

CLI:

```bash
crk-ledger ner-suggest data/cases/<case_slug> --source-id <SOURCE_ID> --limit 80
```

Payload fields: optional `source_id` and `limit`. Creates
`staging/candidates/ner_suggestions_<date>.json`. Output is lead-only and must
not be treated as evidence.

## `linkNames`

Links a caller-provided name list to existing events and co-mentions.

CLI:

```bash
crk-ledger link-names data/cases/<case_slug> --names-file names.txt --name "Primary Name|Alias"
```

Payload fields: `names` and optional `names_file`. The operation resolves
existing entity names, merges overlapping aliases, creates unmatched names as
candidate person entities, refreshes candidate source IDs on rerun, and writes
co-mention event links and relationships only as private, unverified research
leads. It also writes `notes/name_link_research_<date>_<names>.md`.

Safety defaults: `relation_type` is `co_mentioned_in_event` or
`co_mentioned_with`, `status` is `unverified`, `public_export` is `false`, and
confidence is low.

## `validateCase`

Validates case records against required fields and available schemas.

CLI:

```bash
crk-ledger validate data/cases/<case_slug>
```

Returns a success message or validation errors by record type and row index.

## `reportCase`

Writes `exports/evidence_board.md` with source ledger, entities, events, event
links, relationships, claims by status, and redactions/public-output exclusions.
