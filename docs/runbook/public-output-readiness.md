# Public Output Readiness Runbook

Use this runbook before any report, public script, evidence board, Manim export,
chart package, or UFB bundle leaves the local workspace.

## Rule

Every public-facing point must reduce to:

```text
claim -> source_ids -> reliability grade -> confidence/status -> privacy review -> export
```

If that chain is incomplete, keep the point internal, lead-only, disputed, or
excluded from public output.

## Preflight

Validate the ledger and write the evidence board:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py report data/cases/<case_slug>
```

Check the core records before running public gates:

| Record area | Review for |
| --- | --- |
| `records/sources.jsonl` | URL/path, publication metadata, source type, reliability grade, archive/preservation notes, `independence_group`, and `public_export`. |
| `records/claims.jsonl` | `source_ids`, `source_span_ids` when needed, `assertion_type`, `status`, `confidence`, contradiction links, `privacy_review`, and `public_export`. |
| `records/entities.jsonl` | Private-person status, minors, role labels, `privacy_level`, `living_status`, and public-export handling. |
| `records/events.jsonl` | Date precision, source support, confidence/status, and source spans for precise or contested events. |
| `records/relationships.jsonl` and `records/event_links.jsonl` | Source-stated basis, relationship class, confidence/status, and no proximity-based guilt or membership inference. |
| `records/redactions.jsonl` | Public-output blockers, redaction rationale, and unresolved private details. |

## Public Gates

Run the public-export audit. This command fails when public rows include unsafe
or unsupported records unless `--warn-only` is used for triage:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-public-export data/cases/<case_slug>
```

Run the privacy audit and require a redaction log when public output is planned:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-privacy-redactions data/cases/<case_slug> \
  --require-redaction-log
```

Run source-chain review before treating multiple sources as corroboration:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-source-independence data/cases/<case_slug> \
  --fail-on-flags
```

Run narrative readiness with source-span checks for script, report, timeline, or
bundle use:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py review-narrative-readiness data/cases/<case_slug> \
  --require-spans \
  --fail-on-blockers
```

Optional internal triage can include private rows:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py review-narrative-readiness data/cases/<case_slug> \
  --include-private \
  --require-spans
```

## Blockers

Keep rows out of public export when any of these remain unresolved:

- Missing `source_ids` on claims, events, relationships, event links, quotes, or artifacts.
- Precise or contested claims without adequate `source_span_ids`.
- `privacy_review` values that require redaction, exclusion, or manual review.
- Private-person details, minors, home addresses, contact details, private workplaces or schools, medical details, family details, financial identifiers, or weak allegations.
- Claims marked `lead_only`, `single_source` when stronger support is required, `disputed`, `retracted`, or `excluded_from_public_script`.
- Repeated wire copy, press-release reuse, same-publisher chains, or shared archive packets treated as independent corroboration.
- Relationship or event-link rows that infer guilt, motive, membership, or hidden control from proximity.

## Outputs

The review commands write JSON reports under the case `exports/` directory:

| Command | Default output |
| --- | --- |
| `audit-public-export` | `exports/public_export_audit.json` |
| `audit-privacy-redactions` | `exports/privacy_redaction_audit.json` |
| `audit-source-independence` | `exports/source_independence_report.json` |
| `review-narrative-readiness` | `exports/narrative_readiness_review.json` |

Public export can proceed only after blockers are resolved or the affected rows
are kept internal with `public_export: false`.
