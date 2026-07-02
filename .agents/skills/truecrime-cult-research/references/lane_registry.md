<!-- Generated from docs/registry/; edit the registry shards, not this table. -->

# Lane Registry

Lane and extraction-template metadata shared by CLI, MCP, and skills.

## Public Record

| Lane | Skill | Template | Public plan | Use For |
| --- | --- | --- | --- | --- |
| `corporate` | `corporate-financial-records` | `corporate` | yes | Use for corporate registries, securities filings, bankruptcy, ownership, finance, boards, and officers. |
| `education` | `educational-path-records` | `education` | yes | Use for education paths, degrees, attendance, credentials, and academic appointments. |
| `geographical-location` | `geographical-location-intelligence` | `geographical-location` | yes | Use for evidence-item locations, event maps, routes, sightings, map/exhibit locators, and locations-of-interest clusters. |
| `legal-court` | `legal-court-records` | `legal-court` | yes | Use for dockets, filings, orders, hearings, allegations, denials, and court findings. |
| `licensing-professional` | `licensing-professional-records` | `licensing-professional` | yes | Use for professional licenses, board actions, certifications, discipline, sanctions, and credential status. |
| `media-transcript` | `media-transcript-intelligence` | `media-transcript` | yes | Use for timestamped media, speaker turns, transcript claims, quote locators, and media provenance. |
| `missing-persons` | `missing-persons-case` | `missing-persons` | yes | Use for missing-person candidates, last-seen/location-time matching, status updates, unidentified-person comparisons, and privacy-sensitive lead review. |
| `property-location` | `property-location-records` | `property-location` | yes | Use for parcels, deeds, permits, maps, facility locations, and address-sensitive location records. |

## Support

| Lane | Skill | Template | Public plan | Use For |
| --- | --- | --- | --- | --- |
| `identity-resolution` | `identity-resolution` | `identity-resolution` | yes | Use for aliases, duplicate entities, ambiguous public-record identities, entity match evidence, and non-mutating merge-review packets. |
| `public-records-router` | `public-records-router` | `public-records-router` | no | Use for routing a subject or question across court, corporate, education, licensing, property, media, archive, and other public-record lanes. |
| `source-capture` | `source-capture-preservation` | `source-capture` | yes | Use for source preservation, archive URLs, hashes, provenance gaps, and capture metadata. |

## Review

| Lane | Skill | Template | Public plan | Use For |
| --- | --- | --- | --- | --- |
| `contradiction` | `claim-contradiction-audit` | `claim-contradiction` | yes | Use for corrections, denials, retractions, court-finding conflicts, and claim-status review. |
| `foia-open-records` | `foia-open-records-planning` | `foia-open-records` | yes | Use for open-records request planning, agency scope, request wording, exemptions, fee waivers, and appeals. |
| `narrative-readiness` | `narrative-readiness-review` | `narrative-readiness` | no | Use for public script, report, timeline, evidence-board, or bundle readiness review before public use. |
| `privacy-redaction` | `privacy-redaction-audit` | `privacy-redaction` | no | Use for redaction logs, private-person review, minors, addresses, contact details, weak allegations, and public-export blockers. |
| `source-independence` | `source-independence-audit` | `source-independence` | no | Use for source-chain, wire-copy, press-release repetition, same-source-chain, and corroboration independence review. |

## Templates

| Template | File | Notes |
| --- | --- | --- |
| `claim-contradiction` | `extraction_packet_claim_contradiction.json` | Use for contradictions, denials, corrections, retractions, disputed claims, and court-finding-versus-allegation reviews. |
| `corporate` | `extraction_packet_corporate.json` | Use for corporations, nonprofits, investments, bankruptcies, officers, directors, board members, ownership, contracts, and securities or court filings. |
| `education` | `extraction_packet_education.json` | Use for schools attended, degrees, credentials, academic appointments, training, student-era events, alumni claims, and institution affiliations. |
| `foia-open-records` | `extraction_packet_foia_open_records.json` | Use for FOIA, open-records, sunshine-law, public-records request planning, agency scope, request wording, exemptions, fee waivers, and appeal trackers. |
| `generic` | `extraction_packet.json` | Use for general case/source extraction. |
| `geographical-location` | `extraction_packet_geographical_location.json` | Use for evidence-item locations, event geography, routes, sightings, map/exhibit locators, locations of interest, and public-safe map packets. |
| `identity-resolution` | `extraction_packet_identity_resolution.json` | Use for aliases, duplicate entities, ambiguous public-record identities, entity match evidence, and non-mutating merge-review packets. |
| `legal-court` | `extraction_packet_legal_court.json` | Use for public dockets, filings, orders, testimony, opinions, court findings, allegations, denials, parties, attorneys, judges, and hearing timelines. |
| `licensing-professional` | `extraction_packet_licensing_professional.json` | Use for professional licenses, board certifications, disciplinary records, sanctions, employment eligibility, and credential-status public records. |
| `media-transcript` | `extraction_packet_media_transcript.json` | Use for interviews, videos, podcasts, hearings, documentaries, broadcast transcripts, speaker turns, timestamps, quotes, and media provenance. |
| `missing-persons` | `extraction_packet_missing_persons.json` | Use for missing-person, unidentified-person, last-seen, reported-missing, located, recovered, candidate-match, and status-update records. |
| `narrative-readiness` | `extraction_packet_narrative_readiness.json` | Use for public script, report, timeline, evidence-board, or bundle readiness review before public use. |
| `privacy-redaction` | `extraction_packet_privacy_redaction.json` | Use for redaction logs, private-person review, minors, addresses, contact details, weak allegations, and public-export blockers. |
| `property-location` | `extraction_packet_property_location.json` | Use for property records, parcels, deeds, land records, permits, maps, facility locations, and address-sensitive public-location records. |
| `public-records-router` | `extraction_packet_public_records_router.json` | Use for routing a subject or question across court, corporate, education, licensing, property, media, archive, and other public-record lanes. |
| `source-capture` | `extraction_packet_source_capture.json` | Use for source preservation checks, capture metadata, archive URLs, raw/text paths, hashes, and source provenance gaps. |
| `source-independence` | `extraction_packet_source_independence.json` | Use for source-chain, wire-copy, press-release repetition, same-source-chain, and corroboration independence review. |
