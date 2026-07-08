# Review And Export

## Validate And Export

Validate the ledger:

```bash
crk-ledger validate data/cases/harbor_study_circle
crk-ledger report data/cases/harbor_study_circle
```

Review duplicate and ambiguous identity candidates before export:

```bash
crk-ledger dedupe data/cases/harbor_study_circle
crk-ledger resolve-identities data/cases/harbor_study_circle
```

Run public-output audits:

```bash
crk-ledger audit-contradictions data/cases/harbor_study_circle
crk-ledger audit-public-export data/cases/harbor_study_circle
crk-ledger audit-privacy-redactions data/cases/harbor_study_circle
crk-ledger audit-source-independence data/cases/harbor_study_circle
crk-ledger review-narrative-readiness data/cases/harbor_study_circle
```

Export canonical visuals after review:

```bash
crk-ledger export-case-visuals data/cases/harbor_study_circle
```

Export a public-safe Phanestead bundle:

```bash
bun deployment/scripts/tools/export_crk_ufb.mjs data/cases/harbor_study_circle \
  --out data/cases/harbor_study_circle/exports/ufb/harbor_study_circle.ufb_v2
```

Use `--include-private` only for internal review artifacts.

## Good Case Questions

Ask questions that preserve source boundaries:

- What does each source directly state, and which source ID supports it?
- Is this claim a source-stated fact, allegation, denial, court finding,
  self-report, lead-only item, or expert context?
- Is this source independent, or does it repeat another source chain?
- What corrections, denials, retractions, lawsuits, appeals, or later public
  records narrow this claim?
- Does this record include a living private person, minor, address, contact
  detail, medical detail, private family detail, or weak allegation?
- Which claims are safe for a public script, which are internal only, and which
  should be excluded?
- Which timeline events lack precise source spans?
- Which relationships are source-stated, and which are merely co-mentions or
  hypotheses?
- What would change the confidence score?
- What is still unknown or not established?

Avoid questions that force unsupported conclusions:

- Who is obviously guilty?
- Which private people should be exposed?
- Can we infer membership from attendance or proximity?
- Can the agent fill gaps from memory?
- Can repeated copies of the same article count as corroboration?
- Can a route suggestion become an evidence claim?

## Done Criteria

A case pass is ready for public-output review when:

1. Source rows include URL/path, publication metadata, source type,
   reliability grade, and preservation notes where available.
2. Entities, places, artifacts, claims, events, event links, relationships,
   quotes, source spans, and redactions use stable IDs.
3. Every claim has source IDs, status, confidence, and public-export handling.
4. Contradictions, corrections, denials, and missing evidence are recorded.
5. Source independence has been reviewed before marking claims corroborated.
