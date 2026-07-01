# Public Records Routing Matrix

Use this matrix to choose the next skill and extraction template.

| Lane | Skill | Template | Use For |
|---|---|---|---|
| legal-court | `legal-court-records` | `legal-court` | Dockets, filings, orders, hearings, allegations, denials, findings |
| corporate | `corporate-financial-records` | `corporate` | Companies, nonprofits, bankruptcy, ownership, investments, boards, officers |
| education | `educational-path-records` | `education` | Schools, degrees, training, academic appointments, credential disputes |
| licensing-professional | `licensing-professional-records` | `licensing-professional` | Licenses, certifications, professional boards, discipline, sanctions |
| media-transcript | `media-transcript-intelligence` | `media-transcript` | Interviews, hearings, videos, podcasts, documentaries, timestamped claims |
| missing-persons | `missing-persons-case` | `missing-persons` | Missing-person candidates, last-seen/time-location matching, status updates, unidentified-person comparisons |
| geographical-location | `geographical-location-intelligence` | `geographical-location` | Evidence-item locations, event maps, routes, sightings, map/exhibit locators, locations of interest |
| property-location | `property-location-records` | `property-location` | Parcels, deeds, permits, maps, facilities, location-sensitive records |
| source-capture | `source-capture-preservation` | `source-capture` | Archive URLs, hashes, raw/text artifacts, source provenance |
| identity-resolution | `identity-resolution` | `identity-resolution` | Aliases, duplicate entities, ambiguous identities, merge candidates |
| contradiction | `claim-contradiction-audit` | `claim-contradiction` | Corrections, retractions, denials, conflicting claims, findings |

## Safety Order

1. Resolve identity ambiguity before collecting sensitive person-specific records.
2. Preserve source metadata before extracting claims from unstable web sources.
3. Treat legal allegations, license discipline, missing-person records, exact geography, and property/address records as privacy-sensitive until reviewed.
4. Route contradictions and source-independence issues before public narration.
