# TRCR Case Mapping For Legal Court Records

Use existing TRCR ledgers. Preserve court, case number, docket item, document number, page, paragraph, and filing date in `source_spans` or `notes`.

## Sources

Create `sources` for each docket page, filing, order, opinion, transcript, public exhibit, judgment, or legal article. Prefer `source_type: court_record` for court materials and `government_record` for agency adjudication records.

## Entities

Create `entities` for:

- Courts, agencies, law firms, public offices, and institutions.
- Judges, clerks, attorneys, public officials, named parties, trustees, examiners, and public-role witnesses.
- Organizations named as parties, debtors, creditors, regulators, or claimants.

Private individuals, minors, victims, jurors, non-central witnesses, and addresses default to `public_export: false`.

## Claims

Create one claim per precise legal assertion:

- `<Party> filed <filing> in <court> on <date>.`
- `<Filing> alleged <specific allegation>.`
- `<Party> denied <specific allegation>.`
- `<Court> found/ordered/entered <specific finding or order>.`
- `<Case> was dismissed/settled/appealed/affirmed/reversed on <date>.`

Use `claim_type: legal`. Use `assertion_type` to distinguish `allegation`, `denial`, `court_finding`, and `source_stated_fact`.

## Events

Use `events` for public procedural milestones: `case_filed`, `docket_entry`, `motion_filed`, `hearing`, `order_entered`, `judgment_entered`, `charge_filed`, `plea_entered`, `sentencing`, `appeal_filed`, `appeal_decided`, `settlement_entered`.

## Relationships

Use source-stated role relationships:

- `party_to`
- `represented_by`
- `presided_over_by`
- `filed_by`
- `accused_by`
- `denied_by`
- `ordered_by`
- `appealed_by`
- `witness_for`

## Artifacts

Use `artifacts` for important filings, orders, transcripts, exhibits, opinions, judgments, docket sheets, archive captures, and source notes. Set sensitivity and public-export fields according to privacy and sealed-record risks.
