# Intermediate Use

This guide covers review and import work after initial source capture.

## Review Staged Packets

Staged packets live under:

```text
data/cases/<case>/staging/extractions/
```

Before importing, check:

- Every claim has at least one registered source ID.
- Every source-supported claim has a locator or source span.
- Testimony is labeled as testimony.
- Metadata-only sources are not used as fact support.
- Private-person details are redacted or marked for review.
- Disputed or unsupported claims stay `disputed`, `unverified`, or
  `excluded_from_public_script`.

## Import Approved Packets

Import only after review:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger import-extraction \
  data/cases/mkultra_course \
  data/cases/mkultra_course/staging/extractions/<packet>.json
```

Run validation after every import:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger validate data/cases/mkultra_course
```

## Run Review Audits

Use these before writing public prose or export material:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger audit-contradictions data/cases/mkultra_course
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger audit-source-independence data/cases/mkultra_course
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger audit-public-export data/cases/mkultra_course
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger review-narrative-readiness data/cases/mkultra_course --require-spans
```

## Use The Right Research Lane

| Work | Route |
| --- | --- |
| Source preservation | `source-capture-preservation`. |
| Hearing or transcript extraction | `media-transcript-intelligence`. |
| Disputed or conflicting claims | `claim-contradiction-audit`. |
| Public-script readiness | `narrative-readiness-review`. |
| Privacy review | `privacy-redaction-audit`. |
| Corroboration quality | `source-independence-audit`. |

## Done When

- Approved packets are imported.
- Validation passes after import.
- Contradiction, independence, privacy, and readiness checks have been run
  before public output.
