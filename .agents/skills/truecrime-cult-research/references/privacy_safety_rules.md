# Privacy, safety, and public-output rules

## Avoid publishing

- Home addresses or precise residential locations.
- Private phone numbers, emails, usernames used for personal/private purposes.
- Workplace/school details of private people unless central and already widely reported.
- Medical, mental-health, substance-use, or family details unless source-supported, relevant, and handled with care.
- Information about minors except when necessary and already central to public reporting; prefer anonymization.
- Graphic details for shock value.
- Speculative allegations.
- Tactical or operational details that could enable harm.

## Legal/accusation language

Use source-bound language:

- “The article reported…”
- “The court filing alleged…”
- “The witness testified…”
- “The source identifies…”
- “The claim remains disputed because…”

Avoid unsupported language:

- “He was obviously involved…”
- “She must have known…”
- “This proves…”
- “The cult member…” unless sourced and contextually fair.

## Redaction defaults

- Living private person: `public_export: false` unless clearly necessary.
- Minor: `public_export: false` and redacted name.
- Private address/contact info: never export.
- Witness account: export only if source is public and account is necessary.

## Public-export audit

Before public release, run `validate` and review `public_export`,
`privacy_review`, `privacy_level`, and `living_status`. Use
`audit-public-export` when available; otherwise use `report` and
`export-case-visuals` public-readiness outputs as the audit trail. Record the
decision in `research_actions.jsonl`.

## Evidence-board language

Use sections:

- Known from records.
- Corroborated by independent sources.
- Eyewitness/testimonial claims.
- Disputed or contradicted.
- Unknown / not established.
- Excluded from public script.
