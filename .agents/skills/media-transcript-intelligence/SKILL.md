---
name: media-transcript-intelligence
description: Public-source workflow for analyzing interviews, videos, audio, podcasts, hearings, documentaries, broadcasts, captions, and transcripts, then extracting timestamped speaker claims, quotes, source spans, media artifacts, and provenance notes into a TRCR case file. Use when Codex needs transcript intelligence without treating statements as proven facts.
---

# Media Transcript Intelligence

## Operation vocabulary

Lane/template metadata is generated from `docs/lanes.json`; do not invent new lane IDs in this skill doc. Use operation `draft_extraction` with template `media-transcript` for this lane; CLI fallback: `tcr.py draft-extraction ... --template media-transcript`.


## Purpose

Use this skill to turn public media and transcripts into source-traceable TRCR packets. A transcript supports what a speaker said; it does not prove the statement is true without corroborating records.

This skill extends the TRCR case workflow; follow the active truecrime-cult-research safety rules for privacy, source grading, source spans, claims, quotes, and public export boundaries.

## Required Inputs

Establish these before extraction when possible:

- Source URL/path, media title, publisher/platform, date, speaker names, transcript source, captions, or source ID.
- Target case path, normally `tc-c-kit/data/cases/<case_slug>` in this wrapper repo.
- Research question: speaker claims, firsthand/secondhand accounts, timeline statements, contradictions, quotes, media provenance, or transcript review.

If the transcript contains private-person details, minors, addresses, medical details, or weak allegations, keep extracted records non-public until reviewed.

## Workflow

1. **Register and preserve the source.** Use `ingest-url` or `add-source`, then `preserve-source` when raw/text artifacts exist.
2. **Index transcript candidates.** Run `index-transcript` to find timestamp and speaker-line candidates from `text_path`.
3. **Draft the media packet.** Use `draft-extraction --template media-transcript`.
4. **Extract carefully.** Use [case_mapping.md](references/case_mapping.md). Separate direct quotes, speaker claims, interviewer context, narration, captions, and editor notes.
5. **Add source spans.** Use timestamps, line numbers, clip URLs, quote offsets, or episode sections.
6. **Cross-check claims.** Route disputed or important statements through `claim-contradiction-audit` and source-independence review.
7. **Validate and audit.** Run validation and public-export audit before public use.

## Commands

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py index-transcript tc-c-kit/data/cases/<case_slug> <SOURCE_ID>
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID> --template media-transcript
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction tc-c-kit/data/cases/<case_slug> tc-c-kit/data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-contradictions tc-c-kit/data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate tc-c-kit/data/cases/<case_slug>
```

Use `--include-private` on `index-transcript` only for internal review of sources already marked non-public.

## Extraction Rules

- Store one claim per speaker assertion; identify speaker, date, context, and whether it is firsthand, secondhand, commentary, or narration.
- Keep exact quotes short and only when needed; otherwise use summarized claims with `source_spans`.
- Use `assertion_type: self_report` for a speaker's own account, `lead_only` for uncorroborated statements used as leads, and `expert_context` for expert commentary.
- Do not treat captions, edited clips, or transcripts as complete unless source metadata supports completeness.
- Preserve corrections, edits, missing transcript sections, and uncertain speakers in notes.

## Output Expectations

A completed media packet should leave transcript index candidates, source spans with timestamps or line numbers, speaker/source entities, claims and quotes tied to source spans, media artifacts, contradiction notes, and privacy redactions.
