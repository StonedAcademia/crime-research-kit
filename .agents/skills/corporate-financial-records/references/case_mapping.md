# TRCR Case Mapping For Corporate Financial Records

Use existing TRCR ledgers. Keep original filing details in `notes` fields when no dedicated field exists.

## Entities

Create `entities` for:

- Target company: `entity_type: organization`; `role_tags`: `target_company`, `issuer`, `debtor`, `subsidiary`, `parent`, `nonprofit`, or `financial_institution`.
- Board members/directors/officers: `entity_type: person`; `role_tags`: `board_member`, `director`, `officer`, `executive`, `trustee`, `key_employee`, `committee_member`.
- Investors/creditors/lenders/funds: `entity_type: organization` or `person`; `role_tags`: `investor`, `beneficial_owner`, `creditor`, `lender`, `DIP_lender`, `secured_party`, `underwriter`.
- Courts/regulators/exchanges: `entity_type: institution`.
- Filings/documents named as actors only when needed: `entity_type: document`.

Privacy defaults:

- Public company directors/officers named in filings are usually `limited_purpose_public` or `public_figure`, depending on prominence.
- Non-executive employees, individual creditors, claimants, customers, and addresses are private by default.
- Use `public_export: false` where the public-interest reason is not clear.

## Sources

Use `sources.jsonl` for each filing, docket, registry page, annual report, or article.

Important source notes:

- Form type, accession number, CIK/ticker, filing date, period end, page/table, and amendment status.
- Bankruptcy court, case number, chapter, docket/document number, filing date.
- Registry jurisdiction, entity number, status date, annual report year.
- Whether the source is official, self-published, secondary reporting, or lead-only.

## Claims

Create one claim per specific public-record assertion. Examples:

- `<Company> filed Chapter 11 in <court> on <date>.`
- `<Person> was listed as a director of <Company> in the <date> proxy statement.`
- `<Investor> reported beneficial ownership of <percent> of <Company> as of <date>.`
- `<Company> reported total assets/debt/revenue of <amount> for <period>.`
- `<Company> entered a merger agreement with <Counterparty> on <date>.`

Use:

- `claim_type: legal` for bankruptcy, enforcement, litigation, insolvency, sanctions, receivership.
- `claim_type: relationship` for board/officer/investor/subsidiary assertions.
- `claim_type: timeline` or `event` for dated filings and corporate actions.
- `claim_type: background` for neutral company identity and registry status.

Status guidance:

- `verified`: official public record directly supports it and the entity match is clear.
- `single_source`: one official or strong source supports it, but no independent corroboration.
- `corroborated`: multiple independent records align.
- `disputed`: filings or reporting conflict.
- `unverified`: lead-only, ambiguous entity match, stale source, or unclear date.

## Relationships

Use `relationships.jsonl` for links directly supported by filings:

- `board_member_of`
- `director_of`
- `officer_of`
- `executive_of`
- `trustee_of`
- `beneficial_owner_of`
- `investor_in`
- `creditor_of`
- `lender_to`
- `DIP_lender_to`
- `secured_party_to`
- `debtor_in`
- `subsidiary_of`
- `parent_of`
- `affiliate_of`
- `auditor_of`
- `underwriter_for`
- `acquired_by`
- `merged_with`

Set `start_date` and `end_date` only when directly supported. If a filing gives only an "as of" date, put that in notes and avoid treating it as a full tenure.

## Events

Use `events.jsonl` for dated corporate actions:

- `bankruptcy_filing`
- `bankruptcy_plan_confirmed`
- `bankruptcy_sale`
- `financing`
- `funding_round`
- `investment_disclosure`
- `beneficial_ownership_disclosure`
- `director_appointment`
- `director_resignation`
- `officer_change`
- `merger`
- `acquisition`
- `asset_sale`
- `incorporation`
- `dissolution`
- `delisting`
- `enforcement_action`
- `annual_report_filed`
- `proxy_statement_filed`

Attach entity IDs for the company and named counterparties. Attach artifact IDs for key filings or orders.

## Artifacts

Use `artifacts.jsonl` for material documents:

- SEC filing, proxy statement, annual report, bankruptcy petition, first-day declaration, plan/disclosure statement, confirmation order, sale order, financing agreement, merger agreement, annual return, Form 990.
- `artifact_type: document` for filings and orders.
- `sensitivity: medium` or `high` for filings containing addresses, signatures, creditor matrices, account numbers, or large lists of private persons. Use `public_export: false` when needed.

## Contradictions And Currency

Record contradictions when:

- Board rosters differ across filings.
- A company changes name, ticker, jurisdiction, or parent.
- A bankruptcy plan supersedes earlier schedules.
- Amended filings restate financials.
- A source claims current ownership but the filing date is stale.

Prefer notes like: `As-of date only; do not treat as current after YYYY-MM-DD without a newer source.`
