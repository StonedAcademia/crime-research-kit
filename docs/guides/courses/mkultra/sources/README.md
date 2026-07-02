# MKUltra Course Sources

This directory contains the tracked source reference layer for the MKUltra
course. It intentionally excludes raw PDFs, HTML captures, extracted text, and
case records because those live under ignored `data/cases/mkultra_course/`.

| File | Purpose |
| --- | --- |
| [manifest.json](manifest.json) | Source IDs, URLs, metadata, capture status, local raw/text paths, and citation starters. |
| [official-and-archival.md](official-and-archival.md) | Exact citation targets for the core historical guide. |
| [controversy-and-boundaries.md](controversy-and-boundaries.md) | Rules for disputed, testimony-only, OCR-pending, and metadata-only lanes. |

## Reliability Grades

| Grade | Course Meaning |
| --- | --- |
| A | Official, primary, or contemporaneous government source. |
| B | Strong archive, scholarly, or contextual source with provenance. |
| C | Testimony or interpretive source that needs independent support before promotion. |
| D | Lead-only source. Avoid in public output unless explicitly framed as weak. |
| X | Excluded from evidence use. |

## Citation Format

Use this shape in lesson notes and extraction packets:

```text
claim -> source_id -> local path or URL -> locator -> reliability grade -> status
```

Example:

```text
MKULTRA was approved by the DCI on 1953-04-13.
Source: S_SENATE_MKULTRA_1977, raw/sources/S_SENATE_MKULTRA_1977_hearing.txt,
lines 3888-3889, grade A, status source_supported.
```
