# CRK Case Mapping For Privacy Redaction Audit

## Reports

`audit-privacy-redactions` writes `exports/privacy_redaction_audit.json`.

## Redactions

Use `records/redactions.jsonl` for redaction decisions. Include record ID, reason, replacement wording when useful, and source IDs/source spans when the redaction is source-specific.

## Public Export

Set `public_export: false` on unsafe rows. Use `privacy_review: clear` only after the row has been reviewed for public use.
