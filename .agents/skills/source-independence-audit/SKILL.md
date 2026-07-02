---
name: source-independence-audit
description: Source-chain and corroboration workflow for detecting repeated wire copy, press-release repetition, same-source chains, shared authors/publishers, docket/archive reuse, and overstated corroboration in TRCR cases. Use when Codex needs to verify whether multiple sources are genuinely independent before public narration.
---

# Source Independence Audit

## Operation vocabulary

Lane/template metadata is generated from `docs/registry/`; do not invent new lane IDs in this skill doc. Use operation `draft_extraction` with template `source-independence` for this lane; CLI fallback: `tcr.py draft-extraction ... --template source-independence`.


## Purpose

Use this skill to check whether claims, events, event links, or relationships rely on genuinely independent sources. Multiple citations do not equal corroboration when they repeat the same wire story, press release, docket packet, author, publisher, or archive chain.

## Workflow

1. **Run deterministic audit.** Use `source-independence` or `audit-source-independence`.
2. **Review independence groups.** Add or correct `sources[].independence_group` when source provenance is known.
3. **Draft source-chain packet.** Use `draft-extraction --template source-independence` for source-chain findings that need import.
4. **Adjust public claims explicitly.** Do not silently downgrade or upgrade claims; record gaps in notes or later review edits.
5. **Re-run narrative readiness.** Confirm corroboration language is not overstated.

## Commands

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py source-independence tc-c-kit/data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID> --template source-independence
python .agents/skills/truecrime-cult-research/scripts/tcr.py review-narrative-readiness tc-c-kit/data/cases/<case_slug>
```

## Independence Rules

- Treat wire copy, press-release reposts, same publisher, same author, same docket packet, and same archive packet as dependent unless evidence shows independent reporting.
- Primary official records can strongly support a claim, but they are not independent corroboration of themselves.
- Claims marked `corroborated` should usually cite reliable sources from more than one independence group.
- Keep source-chain caveats visible in public narration when needed.

## Output Expectations

A completed audit should leave `exports/source_independence_report.json`, updated source-chain notes where explicitly applied, and a list of claims/events/relationships that need caveats or better independent sourcing.
