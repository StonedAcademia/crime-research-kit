# CRK Case Mapping For Missing-Person Records

Use existing CRK ledgers. Keep candidate matches private by default until reviewed.

## Entities

Create or update entities for:

- Missing person, unidentified person, agency, reporting organization, named official, journalist, or source-stated related organization.
- Use aliases for nicknames, maiden names, alternate spellings, initials, and unidentified-person descriptors.
- Keep minors, living private people, relatives, witnesses, and weak candidates `public_export: false`.

## Places

Create broad public-interest places:

- Jurisdiction, last-known area, route, public event location, agency jurisdiction, recovery area, or redacted sensitive place.
- Use exact places only when already central to public reporting and necessary for the case question.

## Claims

Examples:

- `<Person>` was reported missing on `<date>` according to `<source>.`
- `<Person>` was last seen in `<broad place>` on `<date/time>` according to `<source>.`
- `<Agency>` listed `<case number/status>` for `<person>` on `<date>.`
- `<Source>` later reported `<person>` was located/recovered/identified/misidentified.
- `<Candidate>` is a possible match for `<case/event>` based on source-stated name/location/date overlap.

Use `claim_type: identity`, `timeline`, `location`, `legal`, `background`, or `contradiction`.

## Events

Use events for last seen, last contact, reported missing, bulletin issued, public sighting, vehicle found, search conducted, located, recovered, identified, correction issued, or misidentification corrected.

## Event Links

Link entities to events with conservative relation types:

- `missing_subject`
- `reported_by`
- `last_seen_at`
- `agency_for`
- `located_in`
- `possible_match_to`
- `excluded_match_to`

Keep `possible_match_to` links low confidence and private unless reviewed.

## Relationships

Use only source-stated relationships:

- `reported_missing_by`
- `listed_by`
- `identified_by`
- `same_as`
- `possibly_same_as`
- `not_same_as`
- `associated_with_vehicle`
- `associated_with_location`

## Artifacts

Use artifacts for missing-person bulletins, public database entries, posters, agency releases, maps, case pages, court/coroner records, status-update screenshots, and redaction logs.

## Source Spans

Use source spans for database record IDs, case numbers, bulletin page/paragraph, report paragraph, timestamp, map grid, image caption, archived URL fragment, or exact status wording.

## Redactions

Add redaction rows for minors, private addresses, schools, shelters, medical details, family details, private contact details, graphic recovery details, and weak allegations.
