---
name: claim-contradiction-audit
description: CRK workflow for finding and documenting conflicting claims, denials, corrections, retractions, disputed facts, court findings, timeline conflicts, and source-chain caveats. Use when Codex needs to audit claims before public export or update a case file without smoothing uncertainty into certainty.
---

# Claim Contradiction Audit

## Operation vocabulary

Lane/template metadata is generated from `docs/registry/`; do not invent new lane IDs in this skill doc. Use operation `draft_extraction` with template `claim-contradiction` for this lane; CLI fallback: `crk-ledger draft-extraction ... --template claim-contradiction`.


## Purpose

Use this skill to identify and document conflicts in a CRK case file. The output is a review packet that preserves uncertainty and points to source-backed next actions; it does not automatically resolve disputes or rewrite claim statuses.

This skill extends the CRK case workflow; follow the active truecrime-cult-research safety rules for privacy, source grading, source spans, claims, and public export boundaries.

## Required Inputs

Establish these before audit when possible:

- Target case path, normally `tc-c-kit/data/cases/<case_slug>` in this wrapper repo.
- Claim IDs, source IDs, topic, date range, or public-output script section to review.
- Whether private/internal records should be included in the audit.

If a contradiction involves private people, minors, addresses, weak allegations, or unsupported claims, keep public export blocked until the case is reviewed.

## Workflow

1. **Run deterministic audit.** Use `audit-contradictions` to flag explicit `contradicts` links, opposing assertion types, court-finding conflicts, and status conflicts.
2. **Collect contradiction sources.** Use source lanes from [source_lanes.md](references/source_lanes.md). Prefer corrections, retractions, court findings, amended filings, later official records, and strong follow-up reporting.
3. **Draft contradiction packets.** Use `draft-extraction --template claim-contradiction` for sources that directly contradict, narrow, deny, correct, or retract prior claims.
4. **Map review evidence.** Use [case_mapping.md](references/case_mapping.md). Add `contradicts`, `supports`, `assertion_type`, `source_span_ids`, and status changes only when source-backed.
5. **Check source independence.** Run source-independence audit when corroboration depends on repeated wire copy, press releases, or same-source chains.
6. **Audit public readiness.** Run public-export audit after contradiction review.

## Commands

Use the wrapper-local CRK tool path and prefix case paths with `tc-c-kit/`:

```bash
crk-ledger audit-contradictions tc-c-kit/data/cases/<case_slug>
crk-ledger source-independence tc-c-kit/data/cases/<case_slug>
crk-ledger draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID> --template claim-contradiction
crk-ledger import-extraction tc-c-kit/data/cases/<case_slug> tc-c-kit/data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json
crk-ledger audit-public-export tc-c-kit/data/cases/<case_slug> --warn-only
crk-ledger validate tc-c-kit/data/cases/<case_slug>
```

## Audit Rules

- Treat contradictions as review targets, not as automatic proof one side is false.
- Distinguish explicit contradictions from source-chain caveats, date conflicts, vague wording changes, and new evidence.
- Use `assertion_type: denial` for denials, `court_finding` for findings/orders, `allegation` for allegations, and `source_stated_fact` for neutral source-stated facts.
- Use `status: false_or_retracted` only when a correction, retraction, court record, or reliable source directly supports that status.
- Do not publish weak allegations or contested private-person claims without clear source support, caveats, and privacy review.
- When public-facing text must mention a disputed claim, include the dispute and source basis rather than smoothing it into a single narrative.

## Output Expectations

A completed contradiction audit should leave the case with a JSON contradiction report, source-backed contradiction claims, updated `contradicts` or `supports` links where appropriate, source spans, privacy flags, and clear notes about unresolved disputes.
