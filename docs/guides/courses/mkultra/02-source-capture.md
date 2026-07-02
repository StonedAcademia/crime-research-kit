# Lesson 2: Source Capture And Citations

This lesson builds the source pack for `data/cases/mkultra_course`. Downloaded
documents stay local and ignored. The guide references them through source IDs,
URLs, publication metadata, local raw/text paths, and exact locators.

## Capture Policy

| Source State | Storage | Course Handling |
| --- | --- | --- |
| Reachable PDF or HTML | `raw/downloads/` plus extracted text in `raw/sources/` | Can support claims after locator review. |
| Reachable but image-only scan | Raw PDF plus OCR-needed text marker | Do not cite exact text until OCR succeeds. |
| HTTP blocked or redirect loop | `records/sources.jsonl` metadata only | Keep as lead or citation target; do not support facts. |
| Testimony | Captured source plus speaker context | Extract as testimony, not established fact. |
| Boundary record | Captured source with narrow purpose | Use only for what that source directly supports. |

## Register Sources

Manual registration is useful when a document must be tracked before parsing:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  python .agents/skills/truecrime-cult-research/scripts/tcr.py add-source \
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
  python .agents/skills/truecrime-cult-research/scripts/tcr.py ingest-url \
  data/cases/mkultra_course \
  "https://oversight.house.gov/hearing/mind-control-and-accountability-uncovering-the-truth-of-the-cias-mkultra-project/" \
  --source-type government_record \
  --reliability-grade A
```

After a source is local, preserve it:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  python .agents/skills/truecrime-cult-research/scripts/tcr.py preserve-source \
  data/cases/mkultra_course S_SENATE_MKULTRA_1977
```

## Session Source Pack

The 2026-07-02 pass captured these evidence lanes:

| Lane | Captured Sources |
| --- | --- |
| Core official oversight | `S_SENATE_MKULTRA_1977`, `S_CIA_MKULTRA_IG_1963`, `S_ROCKEFELLER_COMMISSION_1975`. |
| Archive context | `S_NSARCHIVE_DOC01_MKULTRA`, `S_NSARCHIVE_MKULTRA_CONTEXT_2024`. |
| Current oversight | `S_HOUSE_OVERSIGHT_MKULTRA_2026`, `S_HOUSE_KINZER_TESTIMONY_2026`, `S_HOUSE_ONEILL_TESTIMONY_2026`, `S_HOUSE_GINEXI_TESTIMONY_2026`. |
| Boundary records | `S_FBI_FINDERS_VAULT`, `S_FBI_FINDERS_PART_01` through `S_FBI_FINDERS_PART_04`, `S_FBI_JONESTOWN_HISTORY`. |
| Metadata-only blocked captures | `S_DOD_MKSEARCH_1977_METADATA`, `S_CIA_GATEWAY_PROCESS_METADATA`, `S_CIA_STARGATE_OVERVIEW_METADATA`, `S_CIA_MKULTRA_READINGROOM_METADATA`. |

The tracked manifest is [sources/manifest.json](sources/manifest.json). It is
the course-level reference copy. The local canonical ledger remains
`data/cases/mkultra_course/records/sources.jsonl`.

## Extract Text

For text-bearing PDFs:

```bash
pdftotext -layout \
  data/cases/mkultra_course/raw/downloads/S_SENATE_MKULTRA_1977_hearing.pdf \
  data/cases/mkultra_course/raw/sources/S_SENATE_MKULTRA_1977_hearing.txt
```

For image-only scans, run OCR before using exact citations:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[documents]' -- \
  cr-kit ocr-source data/cases/mkultra_course S_FBI_FINDERS_PART_01
```

The Finders FBI Vault PDFs were captured in this session, but their extracted
text sidecars are placeholders. Treat them as OCR pending.

## Build Extraction Packets

Draft packets only after the source has a useful text file or OCR output:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction \
  data/cases/mkultra_course S_CIA_MKULTRA_IG_1963 \
  --template source-capture
```

Fill staged packets with only source-supported records. For each claim, include
`source_ids`, `source_span_ids` or locator notes, reliability grade, confidence,
status, and privacy fields.

## Validate The Local Case

Run validation whenever the source ledger or extraction packets change:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  python .agents/skills/truecrime-cult-research/scripts/tcr.py validate \
  data/cases/mkultra_course
```

Before any public report or video script:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  python .agents/skills/truecrime-cult-research/scripts/tcr.py report \
  data/cases/mkultra_course
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-public-export \
  data/cases/mkultra_course
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-source-independence \
  data/cases/mkultra_course
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  python .agents/skills/truecrime-cult-research/scripts/tcr.py review-narrative-readiness \
  data/cases/mkultra_course --require-spans
```
