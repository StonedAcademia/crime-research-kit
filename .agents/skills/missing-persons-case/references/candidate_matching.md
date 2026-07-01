# Missing-Person Candidate Matching

Use this as a conservative relevance rubric. It ranks leads; it does not prove identity or case relevance.

## Match Signals

Stronger signals:

- Exact name or well-sourced alias match.
- Public source places the person in the same jurisdiction, route, institution, or event area.
- Date missing, last seen, last contact, or report date falls inside the case window.
- Source-stated relationship to an entity, vehicle, organization, facility, or event in the case.
- Independent official or strong secondary source confirms the same status.

Weaker signals:

- Common-name match without age, location, or date support.
- Broad regional overlap only.
- Internet list, wiki, forum, or repost without source provenance.
- Similar circumstances but no source-stated link.

## Suggested Confidence

- `0.8-1.0`: official or strong independent sources support identity, status, date, and location.
- `0.6-0.79`: strong source support with one unresolved gap or source-chain dependency.
- `0.4-0.59`: plausible lead with partial source support; needs corroboration.
- `0.1-0.39`: weak lead, co-mention, common-name match, or broad location/time overlap only.

Use `assertion_type: lead_only`, `status: unverified`, and `public_export: false` for weak or partial candidates.

## Disqualifiers

Mark as not-same-as or excluded when public sources show:

- Different person, jurisdiction, date range, age range, status, or case number.
- A correction, retraction, located-safe update, or misidentification.
- A source-chain issue where every source repeats the same unsupported listing.

## Notes To Preserve

Keep notes about:

- Search terms used.
- Date windows considered.
- Jurisdictions checked.
- Missing source records.
- Why a candidate was retained, excluded, or left unresolved.
