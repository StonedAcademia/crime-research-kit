<!-- Generated from docs/registry/; edit the registry shards, not this table. -->

# Public Records Routing Matrix

Use this matrix to choose the next skill and extraction template.

| Lane | Skill | Template | Public plan | Use For |
| --- | --- | --- | --- | --- |
| `contradiction` | `claim-contradiction-audit` | `claim-contradiction` | yes | Use for corrections, denials, retractions, court-finding conflicts, and claim-status review. |
| `corporate` | `corporate-financial-records` | `corporate` | yes | Use for corporate registries, securities filings, bankruptcy, ownership, finance, boards, and officers. |
| `education` | `educational-path-records` | `education` | yes | Use for education paths, degrees, attendance, credentials, and academic appointments. |
| `foia-open-records` | `foia-open-records-planning` | `foia-open-records` | yes | Use for open-records request planning, agency scope, request wording, exemptions, fee waivers, and appeals. |
| `geographical-location` | `geographical-location-intelligence` | `geographical-location` | yes | Use for evidence-item locations, event maps, routes, sightings, map/exhibit locators, and locations-of-interest clusters. |
| `identity-resolution` | `identity-resolution` | `identity-resolution` | yes | Use for aliases, duplicate entities, ambiguous public-record identities, entity match evidence, and non-mutating merge-review packets. |
| `legal-court` | `legal-court-records` | `legal-court` | yes | Use for dockets, filings, orders, hearings, allegations, denials, and court findings. |
| `licensing-professional` | `licensing-professional-records` | `licensing-professional` | yes | Use for professional licenses, board actions, certifications, discipline, sanctions, and credential status. |
| `media-transcript` | `media-transcript-intelligence` | `media-transcript` | yes | Use for timestamped media, speaker turns, transcript claims, quote locators, and media provenance. |
| `missing-persons` | `missing-persons-case` | `missing-persons` | yes | Use for missing-person candidates, last-seen/location-time matching, status updates, unidentified-person comparisons, and privacy-sensitive lead review. |
| `property-location` | `property-location-records` | `property-location` | yes | Use for parcels, deeds, permits, maps, facility locations, and address-sensitive location records. |
| `source-capture` | `source-capture-preservation` | `source-capture` | yes | Use for source preservation, archive URLs, hashes, provenance gaps, and capture metadata. |

## Safety Order

1. Resolve identity ambiguity before collecting sensitive person-specific records.
2. Preserve source metadata before extracting claims from unstable web sources.
3. Treat legal allegations, license discipline, missing-person records, exact geography, and property/address records as privacy-sensitive until reviewed.
4. Route contradictions and source-independence issues before public narration.
