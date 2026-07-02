# CRK Case Mapping For Property Location Records

Use existing CRK ledgers. Redact private addresses by default.

## Places

Create places for public-interest locations:

- Facility, campus, public building, parcel, broad neighborhood, jurisdiction, or vague area.
- Use `privacy_level`/notes where available and set `public_export: false` for private residences or sensitive places.

## Sources

Use `source_type: government_record` for assessor, recorder, permit, GIS, zoning, and inspection sources. Use `archive` for historical maps/archives and `court_record` for property litigation.

## Claims

Examples:

- `<Parcel>` was listed as owned by `<entity>` on `<date>.`
- `<Permit>` was issued for `<facility>` on `<date>.`
- `<Deed>` transferred `<property>` from `<grantor>` to `<grantee>` on `<date>.`
- `<Facility>` was located in `<jurisdiction>` according to `<source>.`

Use `claim_type: location`, `relationship`, `timeline`, `legal`, or `background`.

## Events

Use events for deed transfer, permit issued, inspection, zoning hearing, facility opened/closed, fire/incident, foreclosure, sale, lease, or map publication.

## Relationships

Use source-stated relationships:

- `owned_by`
- `leased_by`
- `transferred_to`
- `permitted_by`
- `inspected_by`
- `located_in`
- `operated_at`

## Artifacts

Use artifacts for deeds, maps, permit PDFs, assessor cards, GIS screenshots, inspection reports, zoning records, and redaction logs.

## Redactions

Add redaction rows for private-person addresses, exact residence coordinates, contact details, non-public occupants, minors, shelters/safe houses, and private family property.
