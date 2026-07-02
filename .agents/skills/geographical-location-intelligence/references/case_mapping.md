# CRK Case Mapping For Geographical Location Intelligence

Use existing CRK ledgers. Do not create exact points unless the source supports them and privacy review allows them.

## Places

Create or reuse places for:

- Event scene, evidence-item location, route segment, public facility, institution, search area, recovery/find location, jurisdiction, map area, or redacted sensitive place.
- Add aliases for historical names, alternate spellings, source phrasing, facility names, and map labels.
- Use notes for precision, confidence, coordinate source, and redaction rationale.

## Artifacts

Use artifacts for maps, exhibits, photos, videos, GPS/route files, screenshots, public reports, source notes, redaction logs, and map-export packets.

## Claims

Examples:

- `<Source>` places `<event>` at `<place>` with `<precision>` support.
- `<Artifact>` was photographed, found, filed, mapped, or referenced at `<place>` according to `<source>.`
- `<Route>` included `<segment>` according to `<source>.`
- `<Place A>` and `<Place B>` are linked as a location-of-interest cluster for `<research question>` based on source-stated facts.
- `<Location>` is approximate, disputed, corrected, or redacted for public output.

Use `claim_type: location`, `timeline`, `relationship`, `contradiction`, or `background`.

## Events

Use events for sighting, arrival, departure, recovery/find, search, meeting, call/contact, publication of map, exhibit filing, correction, public report release, or location update.

## Event Links

Use event links for source-supported connections:

- `occurred_at`
- `last_seen_at`
- `evidence_found_at`
- `artifact_documented_at`
- `route_passed_through`
- `search_conducted_at`
- `possible_location_for`
- `excluded_location_for`

Weak or approximate links default to `public_export: false`.

## Relationships

Use source-stated relationships:

- `located_at`
- `located_in`
- `near`
- `route_includes`
- `mapped_by`
- `documented_by`
- `recovered_at`
- `photographed_at`
- `redacted_location_of`

## Source Spans

Use source spans for page, paragraph, timestamp, exhibit number, docket item, map sheet/grid, coordinate, route segment, caption, URL fragment, or exact source wording.

## Redactions

Add redaction rows for precise private addresses, homes, minor locations, shelters/safe houses, medical/treatment facilities, private workplaces, and weak lead coordinates.
