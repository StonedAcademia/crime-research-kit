# Initial Use

This guide covers the first source-led workflow: register a source, capture or
parse it, draft an extraction packet, and validate the local case.

## Register A Source

Manual registration is useful when a source must be tracked before parsing:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger add-source \
  data/cases/mkultra_course \
  --title "Project MKULTRA, the CIA's Program of Research in Behavioral Modification" \
  --url "https://www.intelligence.senate.gov/wp-content/uploads/2024/08/sites-default-files-hearings-95mkultra.pdf" \
  --source-type government_record \
  --reliability-grade A \
  --publisher "U.S. Senate Select Committee on Intelligence / Committee on Human Resources" \
  --date-published 1977-08-03
```

For ordinary HTML capture, use `ingest-url`:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger ingest-url \
  data/cases/mkultra_course \
  "https://oversight.house.gov/hearing/mind-control-and-accountability-uncovering-the-truth-of-the-cias-mkultra-project/" \
  --source-type government_record \
  --reliability-grade A
```

## Preserve And Extract Text

Preserve source metadata after capture:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger preserve-source \
  data/cases/mkultra_course S_SENATE_MKULTRA_1977
```

Extract text from text-bearing PDFs:

```bash
pdftotext -layout \
  data/cases/mkultra_course/raw/downloads/S_SENATE_MKULTRA_1977_hearing.pdf \
  data/cases/mkultra_course/raw/sources/S_SENATE_MKULTRA_1977_hearing.txt
```

Run OCR before exact citations on image-only scans:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[documents]' -- \
  cr-kit ocr-source data/cases/mkultra_course S_SOURCE_ID
```

## Draft An Extraction Packet

Draft packets only after the source has useful text or OCR output:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger draft-extraction \
  data/cases/mkultra_course S_CIA_MKULTRA_IG_1963 \
  --template source-capture
```

Every claim needs `source_ids`, locators or source spans, reliability grade,
confidence, status, and privacy fields.

## Validate The Case

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger validate \
  data/cases/mkultra_course
```

## Done When

- At least one source is registered with metadata.
- Captured files and extracted text are stored under the case workspace.
- A staged extraction packet exists for review.
- `crk-ledger validate` passes.
