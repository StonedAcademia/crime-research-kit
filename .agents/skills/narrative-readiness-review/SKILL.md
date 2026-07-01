---
name: narrative-readiness-review
description: Public-output readiness workflow for TRCR scripts, reports, episodes, timelines, Manim exports, and evidence boards. Use when Codex needs to check claim support, source spans, contradictions, source independence, privacy review, caveats, and unsupported narrative points before public use.
---

# Narrative Readiness Review

## Purpose

Use this skill before turning a TRCR case ledger into a public script, report, video, timeline, or evidence board. The review identifies blockers and caveats; it does not rewrite claims automatically.

## Workflow

1. **Run narrative readiness.** Use `review-narrative-readiness` to find source, privacy, confidence, allegation, contradiction, and independence gaps.
2. **Review public-export safety.** Run `audit-public-export` and `audit-privacy-redactions`.
3. **Review contradictions and independence.** Run `audit-contradictions` and `source-independence` for claims used in public narration.
4. **Draft readiness packet when needed.** Use `draft-extraction --template narrative-readiness` for review findings that should be imported as source-backed notes or claims.
5. **Resolve blockers before public use.** Exclude or caveat records that remain unsupported, disputed, private, lead-only, or weakly sourced.

## Commands

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py review-narrative-readiness tc-c-kit/data/cases/<case_slug> --require-spans
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-public-export tc-c-kit/data/cases/<case_slug> --warn-only
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-privacy-redactions tc-c-kit/data/cases/<case_slug> --warn-only
python .agents/skills/truecrime-cult-research/scripts/tcr.py source-independence tc-c-kit/data/cases/<case_slug>
```

## Readiness Rules

- Every public point needs source IDs and source records.
- Allegations need clear wording, source attribution, privacy review, and independent support or explicit caveats.
- Disputed, unverified, false/retracted, excluded, lead-only, and weak claims need exclusion or public-facing caveats.
- Private-person, minor, address/contact, medical, financial, and unsupported private details are not public-ready.

## Output Expectations

A completed review should leave `exports/narrative_readiness_review.json`, blocker/caveat summaries, and a list of claims/events/relationships to exclude, caveat, or improve.
