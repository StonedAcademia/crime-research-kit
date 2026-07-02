# Review And Planning Operations

## `auditPublicExport`

Audits whether a case is ready for public script, report, artifact, or export
use.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-public-export data/cases/<case_slug>
```

Payload fields: `include_private`, `warn_only`, and `out`. The audit fails on
broken references or invalid rows; blocks unresolved privacy review states;
keeps living private people, minors, private contact/location details, weak
allegations, and lead-only co-mentions out of public export; and requires
caveats or exclusion for disputed, unverified, false, retracted, or
public-excluded claims. It writes a `research_actions` row and
`exports/public_export_audit.json` or caller-provided `out`.

## `dedupeRecords`

Reports conservative duplicate candidates for entities, sources, and claims.
The command does not merge or delete evidence rows.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py dedupe data/cases/<case_slug>
```

Payload fields: `record_type`, `min_key_chars`, and `out`. Writes
`staging/candidates/dedupe_report_<date>.json` or caller-provided `out`, plus a
`research_actions` row with `action: dedupe`.

## `preserveSource`

Computes preservation metadata for an existing source and writes a JSON report.
This operation updates only the source row's preservation metadata and does not
create evidence records.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py preserve-source data/cases/<case_slug> <SOURCE_ID>
```

Payload fields: `source_id`, `archive_url`, `content_type`, and `out`. Writes
`exports/source_preservation/<SOURCE_ID>.json` or caller-provided `out`.

## `resolveIdentities`

Reports conservative identity-resolution candidates for entities with matching
names or aliases. The command does not merge, delete, or publicly identify
records.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py resolve-identities data/cases/<case_slug>
```

Payload fields: `min_key_chars`, `include_merged`, and `out`. Writes
`staging/candidates/identity_resolution_<date>.json` or caller-provided `out`.

## `auditContradictions`

Reports explicit and likely claim contradictions. This command identifies
review targets and does not change claim status, confidence, or public-export
flags.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-contradictions data/cases/<case_slug>
```

Payload fields: `include_private`, `min_overlap`, `fail_on_flags`, and `out`.
Writes `exports/claim_contradiction_audit.json` or caller-provided `out`.

## `planPublicRecords`

Writes a source-lane plan for a subject. This is a planning artifact only; it
does not create evidence claims or imply misconduct, identity, or relationships.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py plan-public-records data/cases/<case_slug> --subject "<subject>"
```

Payload fields: `subject`, `question`, repeated `lane`, and `out`. Supported
`lane` values come from `docs/registry/` entries with `public_record_plan`. The
generated routing table is
`.agents/skills/public-records-router/references/routing_matrix.md`.

## `indexTranscript`

Indexes timestamp and speaker-line candidates from registered source text. The
report helps create source spans and quotes but does not import claims or
quotes.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py index-transcript data/cases/<case_slug> <SOURCE_ID>
```

Payload fields: `source_id`, `max_segments`, `include_private`, and `out`.
Writes `staging/candidates/transcript_index_<source_id>_<date>.json`.

## `planOpenRecords`

Writes a FOIA/open-records request plan. This is a planning artifact and does
not prove that records exist.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py plan-open-records data/cases/<case_slug> --subject "<subject>" --agency "<agency>"
```

Payload fields: `subject`, `agency`, optional `jurisdiction`, `law`,
`date_range`, repeated `record`, and `out`. Writes
`staging/candidates/open_records_plan_<subject>_<date>.json`.

## `reviewNarrativeReadiness`

Reports blockers and caveats before public narrative use. This command does not
rewrite claims, events, relationships, or public-export flags.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py review-narrative-readiness data/cases/<case_slug>
```

Payload fields: `include_private`, `require_spans`,
`min_independent_sources`, `fail_on_blockers`, and `out`. Writes
`exports/narrative_readiness_review.json`.

## `auditPrivacyRedactions`

Reports privacy and redaction blockers before public output.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-privacy-redactions data/cases/<case_slug>
```

Payload fields: `include_private`, `require_redaction_log`, `warn_only`, and
`out`. Writes `exports/privacy_redaction_audit.json`.

## `auditSourceIndependence`

Reports repeated wire copy, press-release repetition, and same-source-chain
support risks. The `source-independence` alias is equivalent to
`audit-source-independence`.

CLI:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py source-independence data/cases/<case_slug>
```

Payload fields: `include_private`, `min_title_chars`, `fail_on_flags`, and
`out`. Writes `exports/source_independence_report.json`.
