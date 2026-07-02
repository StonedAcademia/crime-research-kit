---
name: criminal-research
description: Source-backed criminal research and academic forensic analysis workflow for M.O., offense patterns, victimology, behavioral signatures, escalation, criminological context, and non-diagnostic personality hypotheses in CRK case files. Use when Codex needs to analyze criminal behavior, offender narratives, case typologies, or forensic psychology concepts without inferring guilt, diagnosing people, or treating unsourced profile claims as evidence.
---

# Criminal Research

## Operation vocabulary

Lane/template metadata is generated from `docs/registry/`; do not invent new lane IDs in this skill doc. Use operation `draft_extraction` with template `criminal-research` for this lane; CLI fallback: `crk-ledger draft-extraction ... --template criminal-research`.

## Purpose

Use this skill to turn public, source-backed material into careful criminological and forensic-behavioral analysis. The output should describe observed M.O. elements, victimology, offense scripts, escalation, staging, source-stated behavioral traits, and academic context without presenting a profile as proof.

This skill extends the CRK case workflow; follow the active truecrime-cult-research safety rules for privacy, source grading, source spans, claims, and public export boundaries.

## Required Inputs

Establish these before analysis when possible:

- Target case path, normally `tc-c-kit/data/cases/<case_slug>` in this wrapper repo.
- Source IDs or public sources that directly support the behavior, offense pattern, expert context, or typology being analyzed.
- Research question: M.O., victimology, escalation, forensic psychology context, offender narrative, crime-scene behavior, or comparison across source-backed events.

If the subject is a living private person, unnamed suspect, minor, or weakly sourced target, keep analysis internal and non-public until privacy and legal/court review are complete.

## Workflow

1. **Register sources first.** Use `ingest-url` or `add-source`; use source-capture preservation for unstable web material.
2. **Separate evidence from interpretation.** Extract directly observed behavior and source-stated expert analysis as claims before adding hypotheses.
3. **Draft the criminal-research packet.** Use `draft-extraction --template criminal-research`.
4. **Apply forensic lenses.** Use [forensic_lenses.md](references/forensic_lenses.md) to separate M.O., signature-like behavior, victimology, staging, escalation, and typology.
5. **Map outputs to the ledger.** Use [case_mapping.md](references/case_mapping.md). Every interpretation needs source IDs, source spans, confidence, and status.
6. **Route caveats.** Use legal/court records for allegations, contradiction review for disputed claims, source-independence review for repeated profile narratives, and narrative-readiness review before public output.

## Commands

```bash
crk-ledger draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID> --template criminal-research
crk-ledger audit-contradictions tc-c-kit/data/cases/<case_slug>
crk-ledger source-independence tc-c-kit/data/cases/<case_slug>
crk-ledger audit-public-export tc-c-kit/data/cases/<case_slug> --warn-only
crk-ledger validate tc-c-kit/data/cases/<case_slug>
```

## Analysis Rules

- Do not diagnose personality disorders, psychopathy, sadism, narcissism, delusion, or mental illness unless a cited qualified source or court record states it. Even then, preserve the source wording and context.
- Treat profiles, typologies, and behavioral hypotheses as analytical claims with `status: unverified`, `single_source`, or `disputed` until corroborated.
- Separate M.O. from motive and from signature-like behavior. M.O. is functional behavior described by sources; motive and intent require source-backed wording.
- Do not infer guilt, identity, membership, intent, escalation, or criminal responsibility from similarity alone.
- Avoid operational detail that would teach evasion, concealment, victim targeting, or crime commission. Summarize at a safe, educational level.
- Prefer academic, court, official, and strong investigative sources over sensational media or profile-driven retellings.

## Output Expectations

A completed packet should leave source-backed behavioral claims, event links, relationship links where directly supported, short expert-context claims, notes on uncertainty and alternative explanations, source spans, privacy flags, and public-export blockers for weak or diagnostic claims.
