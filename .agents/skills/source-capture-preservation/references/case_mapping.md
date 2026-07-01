# TRCR Case Mapping For Source Capture Preservation

Use existing TRCR ledgers. Preservation metadata belongs on source rows and preservation reports; source-backed facts belong in claims, events, relationships, and artifacts.

## Sources

Source records may use these optional fields:

- `archive_url`
- `content_type`
- `capture_method`
- `capture_timestamp`
- `preservation_checked_at`
- `raw_sha256`
- `text_sha256`
- `raw_size_bytes`
- `text_size_bytes`
- `preservation_status`
- `preservation_warnings`

Use `preservation_status: captured`, `registered_with_archive`, `metadata_only`, or `missing_artifacts`.

## Artifacts

Use `artifacts` for important preserved materials: raw download, extracted text, PDF, docket document, transcript, screenshot/image, archive capture, source note, and redaction log.

## Source Spans

Use `source_spans` for precise locators such as page, paragraph, timestamp, quote offset, docket item, accession number, exhibit, or archive capture reference.

## Claims

Create claims only for source-supported provenance assertions when needed:

- `<Source>` was captured from `<URL>` on `<date>.`
- `<Document>` is docket item `<number>` in `<case>.`
- `<Archive>` captured `<URL>` on `<date>.`
- `<Source>` is a mirror/repost and the original source was not available.

Use `claim_type: background` or `legal` depending on the source context.

## Research Actions

Every preservation command should log a `research_actions` row with the source ID, report path, status, and warnings.
