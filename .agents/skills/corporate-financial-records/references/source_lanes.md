# Corporate Public Record Source Lanes

Use official sources first, then corroborate with strong secondary reporting. If a source is a commercial database or scraped aggregator, treat it as a lead unless it links to the underlying filing.

## United States Public Companies

- SEC EDGAR company search: identify CIK, ticker history, filing dates, accession numbers, and primary documents.
- SEC submissions/companyfacts APIs: useful for structured filing lists and XBRL facts; still cite the filing or accession used.
- Form 10-K / 10-Q: business, risk factors, financial statements, debt, subsidiaries, legal proceedings, executive officers.
- Form 8-K: material events, bankruptcies, financings, board changes, auditor changes, delistings, acquisitions.
- DEF 14A proxy: directors, nominees, board committees, compensation, beneficial ownership tables, related-party transactions.
- Forms 3/4/5: insider positions and transactions; do not infer motive from trades.
- Schedule 13D/13G: beneficial ownership and activist positions.
- Form 13F: institutional investment manager holdings; note report date and that positions can be stale.
- Form D: exempt offerings and private placements; use for issuer, offering amount, related persons, and sales-compensation facts.
- S-1/S-3/S-4/424B: offerings, mergers, risk factors, selling shareholders, transaction terms.

## United States Private Companies And Nonprofits

- Secretary of State / corporate registry: legal name, status, registration date, jurisdiction, registered agent, officers/directors where public.
- State annual reports: officers/directors, principal office, status changes, mergers, dissolutions.
- UCC filings: secured-party/debtor leads; verify relevance before adding claims.
- County recorder or land records: use only for public-interest entity-level property/security instruments; redact private addresses.
- IRS Tax Exempt Organization Search and Form 990: nonprofit officers/directors, compensation, grants, contractors, related organizations.
- Regulator portals: banking, insurance, charity, procurement, campaign-finance, securities, professional licensing, and enforcement databases.

## Bankruptcy And Court Records

- PACER/CM/ECF or court-hosted docket pages: authoritative docket entries, case number, chapter, debtor, judge, filing date, claims register where available.
- CourtListener RECAP: public mirror of PACER documents; cite docket/document number and verify against court metadata when possible.
- Bankruptcy petition, schedules, statement of financial affairs, first-day declaration, creditor matrix, claims register, plan, disclosure statement, confirmation order, sale motions, DIP financing orders, trustee/examiner reports.
- SEC 8-K or foreign exchange releases may disclose bankruptcy, administration, receivership, restructuring support agreements, or going-concern warnings.

## Non-US Corporate Registries

- UK Companies House: company status, filings, officers, persons with significant control, charges, insolvency records.
- Canada SEDAR+ and provincial registries: issuer filings and corporate registration details.
- EU national business registers and insolvency registers: verify jurisdiction-specific coverage.
- Foreign exchange filings: annual reports, notices of substantial shareholding, board changes, suspensions, delistings.
- Sanctions/export-control/procurement debarment registries: use only when the entity is clearly matched.

## Investment And Ownership Lanes

- Official securities filings: 13D/13G, 13F, Form D, prospectuses, annual reports, proxy beneficial ownership tables.
- Corporate transaction filings: merger agreements, asset purchase agreements, tender offers, scheme documents, disclosure statements, sale orders.
- Bankruptcy sale and financing records: stalking horse bids, asset purchase agreements, DIP lenders, credit bids, creditor committees.
- Regulator and exchange announcements: investment approvals, banking changes in control, insurance holding-company filings.
- Press releases and company websites: useful for issuer-stated investment announcements; grade and note as self-reported unless corroborated.
- Reputable financial journalism: useful for context and contradictions; do not treat unnamed-source reporting as official fact.

## Board And Officer Lanes

- DEF 14A, 10-K Item 10, 8-K Item 5.02, annual reports, foreign exchange notices.
- State annual reports or corporate registry officer pages where they list directors/officers.
- Nonprofit Form 990 Part VII for officers, directors, trustees, key employees, and highest compensated employees.
- Bankruptcy first-day declarations and board resolutions attached to filings can identify authorized officers and special committees.
- Company governance pages are self-published; use them for current roster leads and corroborate through filings when possible.

## Source Grading Defaults

- `A`: court docket/filing, SEC/regulator filing, state registry record, official bankruptcy document, audited public filing.
- `B`: reputable financial/legal journalism, exchange notice, audited annual report hosted by issuer when not independently filed.
- `C`: company website, press release, investor presentation, commercial database page, biographical profile, nonprofit self-description.
- `D`: uncited aggregator, forum/social post, lead-only database row, reposted filing without provenance.
- `X`: AI summaries, unverifiable claims, leaked/private material without permission, fabricated or provenance-free records.
