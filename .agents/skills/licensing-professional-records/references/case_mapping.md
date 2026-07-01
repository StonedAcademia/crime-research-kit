# TRCR Case Mapping For Licensing Professional Records

Use existing TRCR ledgers. Keep license identifiers in source spans or notes.

## Sources

Use `source_type: government_record` for board or regulator sources, `court_record` for legal orders, `official_report` for official disciplinary reports, and `news_article` for reputable coverage.

## Entities

Create entities for:

- Licensed person or organization.
- Licensing board, regulator, certifying body, court, employer, or professional association.

Private people and non-central complainants default to `public_export: false`.

## Claims

Examples:

- `<Person>` was listed as holding license `<number>` in `<jurisdiction>` as of `<date>.`
- `<Board>` listed `<license>` as active/expired/suspended/revoked on `<date>.`
- `<Board>` entered disciplinary order `<number>` on `<date>.`
- `<Person>` self-reported credential `<credential>` in `<source>.`

Use `claim_type: identity`, `relationship`, `legal`, or `background` as appropriate.

## Events

Use events for license issued, status changed, complaint filed, board order entered, sanction imposed, suspension/revocation, reinstatement, certification awarded, or credential dispute.

## Relationships

Use source-stated relationships:

- `licensed_by`
- `certified_by`
- `disciplined_by`
- `sanctioned_by`
- `employed_as`
- `credential_claimed_by`
- `credential_disputed_by`
