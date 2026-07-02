---
name: source-capture-preservation
description: Public-source preservation workflow for TRCR cases. Capture or register URLs/files, record archive URLs, hash raw and extracted text artifacts, document provenance gaps, and prepare sources for extraction. Use when Codex needs to preserve evidence-chain metadata before claims are imported or exported.
---

# Source Capture Preservation

## Operation vocabulary

Lane/template metadata is generated from `docs/lanes.json`; do not invent new lane IDs in this skill doc. Use operation `draft_extraction` with template `source-capture` for this lane; CLI fallback: `tcr.py draft-extraction ... --template source-capture`.


## Purpose

Use this skill to make source records reproducible and auditable before extracting facts. Preservation metadata supports the evidence chain; it does not make a source substantively reliable by itself.

This skill extends the TRCR case workflow; follow the active truecrime-cult-research safety rules for privacy, source grading, source spans, claims, and public export boundaries.

## Required Inputs

Establish these before preservation when possible:

- Target case path, normally `tc-c-kit/data/cases/<case_slug>` in this wrapper repo.
- Source URL, archive URL, local file path, docket/accession/document number, content type, and source type.
- Whether the source is original, mirror/archive, extracted text, screenshot/image, transcript, or lead-only reference.

If a source cannot be captured, register metadata and explain the gap in notes. Do not fabricate text or cite an AI-generated summary as evidence.

## Workflow

1. **Register or ingest the source.** Use `ingest-url` for fetchable public URLs and `add-source` for records that must be manually registered.
2. **Preserve metadata.** Run `preserve-source` to compute hashes for existing raw/text artifacts and write a source-preservation report.
3. **Record archive context.** Store archive URL, original URL, content type, capture date, access notes, and missing-artifact warnings.
4. **Draft capture packet when needed.** Use `draft-extraction --template source-capture` for sources where provenance itself needs extraction or redaction review.
5. **Map preservation to the case.** Use [case_mapping.md](references/case_mapping.md). Put factual claims in normal records only when a source supports them.
6. **Audit before public use.** Run validation and public-export audit; source metadata can contain private identifiers in paths or notes.

## Commands

Use the wrapper-local TRCR tool path and prefix case paths with `tc-c-kit/`:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py ingest-url tc-c-kit/data/cases/<case_slug> "<URL>" \
  --source-type news_article \
  --reliability-grade B \
  --archive-url "<archive URL if available>"

python .agents/skills/truecrime-cult-research/scripts/tcr.py preserve-source tc-c-kit/data/cases/<case_slug> <SOURCE_ID>
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID> --template source-capture
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-public-export tc-c-kit/data/cases/<case_slug> --warn-only
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate tc-c-kit/data/cases/<case_slug>
```

## Preservation Rules

- Prefer original sources and official archives over reposts or screenshots.
- Store `archive_url` when available and note the archive capture date if visible.
- Use hashes to detect local artifact drift; do not treat a hash as proof the source is truthful.
- Keep source-chain caveats in notes: mirror, repost, wire copy, press release, transcript needed, OCR needed, paywalled, missing attachment, stale capture.
- Do not place private contact details, addresses, credentials, tokens, cookies, account IDs, or downloaded private material in source notes or public exports.
- Use `source_type: social_media_lead` and grade `D` for social posts or threads that are only leads.

## Output Expectations

A completed preservation pass should leave source records with capture metadata, hashes where local artifacts exist, archive URLs where available, preservation warnings, a JSON preservation report, and research-action logs for repeatability.
