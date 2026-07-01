# Topic extraction templates

Use these as source-packet checklists. They do not replace the safety rules or
the source-quality rubric.

## Baseline case packet

- Sources: register the article, record, interview, archive item, or book before extraction.
- Entities: named people, groups, institutions, publications, documents, vehicles, and relevant objects.
- Claims: one assertion per row, with `source_ids`, `status`, `confidence`, `privacy_review`, and optional `source_spans`.
- Events: dated or approximate occurrences, with honest `date_precision`.
- Event links: entity-to-event edges only; co-mentions stay lead-only unless source-stated.
- Relationships: source-stated or carefully qualified edges between entities.
- Redactions: private-person, minor, contact, address, medical, and weak allegation issues.

## Corporate, organization, and financial packet

Route this lane to `corporate-financial-records` when the main task is about a
corporation, nonprofit, bank, shell company, bankruptcy, investment, board,
officer, ownership, funding, transaction, or financial record.

- Sources: SEC/state filings, regulator records, court or bankruptcy dockets, annual reports, audited statements, official registries, and strong reporting.
- Entities: legal entities, subsidiaries, officers, directors, investors, creditors, debtors, auditors, trustees, and committees.
- Claims: legal status, filing facts, board/officer facts, ownership or beneficial ownership claims, investment amounts, bankruptcy facts, and material transaction facts.
- Events: incorporation, registration change, appointment, resignation, filing, financing, merger, acquisition, delisting, bankruptcy petition, plan confirmation, sale, or liquidation.
- Relationships: `director_of`, `officer_of`, `investor_in`, `creditor_of`, `debtor_in`, `subsidiary_of`, `affiliate_of`, `auditor_for`, `trustee_for`.
- Guardrails: do not infer fraud, hidden control, shell purpose, or misconduct from structure alone. Redact addresses, account numbers, private creditors, and non-central employees.

## Education path packet

Route this lane to `educational-path-records` when the main task is about
schools, attendance, degrees, training, credentials, academic appointments,
alumni claims, student-era events, or institution affiliations.

- Sources: official biographies, institution pages, catalogs, public archives, court records, licensing records, dissertations, academic publications, and reputable reporting.
- Entities: person, schools, departments, credentialing bodies, student organizations, publications, and relevant archives.
- Claims: attended, enrolled, graduated, degree awarded, studied subject, trained at, taught at, researched at, affiliated with, honorary degree, or claimed-but-unverified.
- Events: enrollment, graduation, appointment, resignation, publication, credential grant, credential revocation, or public credential dispute.
- Relationships: `attended`, `graduated_from`, `degree_from`, `trained_at`, `taught_at`, `appointed_to`, `affiliated_with`, `published_with`.
- Guardrails: do not seek private records, grades, transcripts, disciplinary records, student IDs, dorm/home addresses, private emails, or non-public classmates. Do not infer friendship, influence, ideology, or membership from co-attendance.

## Legal and court records packet

Route this lane to `legal-court-records` when the task is mainly about public
dockets, filings, court orders, opinions, hearings, judgments, party roles,
allegations, denials, court findings, appeals, or legal posture.

- Sources: court-hosted dockets, filings, orders, opinions, hearing transcripts, public exhibits, CourtListener/RECAP mirrors, official regulator records, and strong legal reporting.
- Entities: courts, judges, clerks, parties, attorneys, law firms, agencies, witnesses, experts, debtors, creditors, trustees, and named organizations.
- Claims: case identity, party role, filing facts, allegations, denials, court findings, orders, judgments, dispositions, appeals, and procedural posture.
- Events: case filing, docket entry, motion filing, hearing, order entered, judgment entered, plea, sentencing, appeal, settlement, bankruptcy filing, or plan confirmation.
- Relationships: `party_to`, `represented_by`, `presided_over_by`, `filed_by`, `accused_by`, `denied_by`, `ordered_by`, `appealed_by`, `witness_for`.
- Guardrails: distinguish allegations, denials, and findings with `assertion_type`; redact minors, addresses, sealed details, victim/private-person contact details, and non-public identifiers.

## Identity-resolution packet

Route this lane to `identity-resolution` when the task is about aliases,
duplicate people or organizations, ambiguous public-record identities, entity
merge candidates, or conflicts over whether two records describe the same actor.

- Sources: official records with names and roles, public biographies, court records, institutional pages, filings, archived pages, and strong reporting.
- Entities: candidate people or organizations, alias records, public roles, jurisdictions, institutions, courts/agencies, and source documents.
- Claims: alias/name variant, same-person/entity assertion, role match, date/jurisdiction match, conflicting identity signal, or insufficient evidence.
- Relationships: `alias_of`, `possibly_same_as`, `not_same_as`, `held_role_at`, `named_in_record`, `associated_with_identifier`.
- Guardrails: do not auto-merge; keep candidates `status: unverified`, `public_export: false`, and privacy reviewed until source-backed.

## Source-capture and preservation packet

Route this lane to `source-capture-preservation` when the task is about source
capture metadata, archive URLs, raw/text artifacts, checksums, provenance gaps,
or whether a source is preserved well enough for later extraction.

- Sources: original URL, archive URL, official mirror, local file, court/document identifier, accession number, docket item, and capture timestamp.
- Artifacts: raw download, extracted text, PDF, transcript, image/screenshot, archive capture, docket document, source note, and redaction log.
- Claims: source origin, capture status, archive status, official-record identifier, provenance gap, redaction/privacy risk, and source-chain caveat.
- Events: capture, archive lookup, source update, correction/retraction publication, docket filing, or source disappearance.
- Guardrails: AI summaries and provenance-free mirrors are leads only; preserve hashes but do not treat a checksum as substantive evidence.

## Claim-contradiction audit packet

Route this lane to `claim-contradiction-audit` when the task is mainly about
corrections, retractions, denials, court findings, disputed wording, date
conflicts, source-chain caveats, or public-readiness of contested claims.

- Sources: correction notices, retractions, later interviews, court findings, appeals, amended filings, official reports, strong investigative follow-ups, and contradictory firsthand accounts.
- Claims: explicit contradiction, denial, correction, retraction, date conflict, court finding conflict, source-chain caveat, or unsupported public claim.
- Events: correction issued, retraction issued, court finding entered, appeal decided, amended filing posted, or testimony contradicted.
- Relationships/event links: use only when the contradiction source directly ties an entity to an event or another entity; otherwise attach claim IDs and source spans.
- Guardrails: do not resolve disputed facts unless a source supports the resolution; preserve uncertainty in `status`, `confidence`, `contradicts`, `supports`, and notes.

## Public-records router packet

Route this lane to `public-records-router` when the task is mainly about
deciding which source lanes to pursue before extraction.

- Sources: existing case sources, known URLs, subject aliases, jurisdictions, agencies, dates, and constraints.
- Claims: route suggestions, jurisdiction constraints, record identifiers, access caveats, privacy blockers, and lead-only search plans.
- Artifacts: source-plan report, notes, query lists, and public-record checklist.
- Guardrails: route suggestions are not evidence. Do not create public claims from a source plan alone.

## Licensing and professional-record packet

Route this lane to `licensing-professional-records` when the task is about
professional licenses, certifications, board registrations, discipline,
sanctions, suspensions, revocations, or credential disputes.

- Sources: official board lookups, disciplinary orders, consent agreements, certification bodies, regulator records, institutional profiles, and strong reporting.
- Entities: licensed person, licensing board, regulator, certifying body, employer, professional association, and court/agency.
- Claims: license status, status date, license number, credential awarded, disciplinary action, sanction, suspension, revocation, reinstatement, or credential dispute.
- Events: license issued, status changed, complaint filed, board order entered, sanction imposed, reinstatement, or dispute published.
- Relationships: `licensed_by`, `certified_by`, `disciplined_by`, `sanctioned_by`, `employed_as`, `credential_claimed_by`, `credential_disputed_by`.
- Guardrails: do not infer misconduct, competence, employment, or identity from a lookup alone. Redact private addresses, complaint details involving private people, and personal identifiers.

## Media and transcript packet

Route this lane to `media-transcript-intelligence` when the task is about
interviews, podcasts, hearings, broadcasts, documentaries, captions,
transcripts, timestamped claims, speakers, or quote locators.

- Sources: original media, official transcripts, captions, hearing transcripts, broadcast archives, documentary pages, and reputable publisher transcripts.
- Entities: speakers, interviewers, subjects, publishers, producers, media platforms, transcript providers, and organizations named in the media.
- Claims: speaker statement, firsthand account, secondhand account, interviewer context, narration, caption note, transcript provenance, correction, or follow-up.
- Events: interview recorded, media published, hearing held, statement made, transcript published, correction issued, or follow-up published.
- Relationships: `interviewed_by`, `interviewed`, `said_in_interview`, `appeared_in`, `published_by`, `transcribed_by`.
- Guardrails: a transcript proves what was said, not that the statement is true. Keep exact quotes short and link timestamps/lines with `source_spans`.

## Property and location packet

Route this lane to `property-location-records` when the task is about property,
parcels, deeds, permits, zoning, maps, facilities, campuses, public buildings,
or address-sensitive location history.

- Sources: assessor, recorder, deed, parcel, GIS, permit, zoning, inspection, court, archive, institutional map, and strong reporting.
- Entities: property owner, organization owner, trust/LLC, facility operator, permit applicant, government office, and inspector.
- Places: parcel, facility, campus, public building, jurisdiction, vague area, or redacted private address.
- Claims: parcel identity, transfer, ownership/trust record, permit, inspection, zoning, facility location, address redaction need, or boundary/map context.
- Events: deed transfer, permit issued, inspection, zoning hearing, facility opened/closed, foreclosure, sale, lease, map publication.
- Relationships: `owned_by`, `leased_by`, `transferred_to`, `permitted_by`, `inspected_by`, `located_in`, `operated_at`.
- Guardrails: private addresses, home coordinates, minor-related locations, shelters/safe houses, and non-central family property default to `public_export: false`.

## Missing-persons packet

Route this lane to `missing-persons-case` when the task is about
missing-person candidates, unidentified persons, last-seen or last-contact
records, public bulletins, located/recovered status updates, or matching by
name, alias, location, date range, vehicle, or source-stated related entity.

- Sources: official bulletins, public missing-person database entries, agency releases, public unidentified-person records, court/coroner records when public, strong local reporting, and status updates.
- Entities: missing person, unidentified person, agency, public database, reporting organization, vehicle, and source-stated related entities.
- Places: last-known area, reported-missing jurisdiction, route or travel area, sighting area, recovery/find area, and redacted sensitive location.
- Claims: identity/status, last seen/contact, reported missing, located/recovered/identified, possible match, excluded match, misidentification, correction, or privacy blocker.
- Events: last seen, last contact, reported missing, bulletin issued, sighting reported, search conducted, vehicle/artifact found, located, recovered, identified, correction, or misidentification.
- Relationships/event links: `reported_missing_by`, `listed_by`, `identified_by`, `possibly_same_as`, `not_same_as`, `associated_with_vehicle`, `associated_with_location`, `missing_subject`, `last_seen_at`.
- Guardrails: candidates are lead-only until source-supported. Minors, private-person details, exact homes/schools/shelters/workplaces, family details, medical details, and weak leads default to `public_export: false`.

## Geographical-location packet

Route this lane to `geographical-location-intelligence` when the task is about
evidence-item locations, event maps, routes, sightings, search areas, map or
exhibit locators, place alias reconciliation, or locations-of-interest clusters.
Use `property-location-records` instead for parcel ownership, deeds, permits,
zoning, or address-record research.

- Sources: maps, public reports, court exhibits, filings, photos/videos, transcripts, captions, official GIS/map pages, historical maps, archives, and strong reporting with location support.
- Places: event scene, evidence find location, route segment, public facility, jurisdiction, search area, location of interest, and redacted sensitive place.
- Artifacts: maps, exhibits, photos, videos, transcripts, route files, public reports, map-export packets, and redaction logs.
- Claims: event location, evidence-item location, last-seen location, route/movement, search area, map/exhibit locator, location-of-interest cluster, approximate/disputed location, or sensitive-location redaction.
- Events: occurred at, last seen at, arrival/departure, evidence found, search conducted, route documented, map published, or location corrected.
- Relationships/event links: `located_at`, `located_in`, `near`, `route_includes`, `mapped_by`, `documented_by`, `recovered_at`, `photographed_at`, `redacted_location_of`, `evidence_found_at`.
- Guardrails: preserve precision separately from confidence. Do not turn vague locations into exact coordinates; exact private, minor-related, shelter, medical, or weak-lead locations default to non-public.

## FOIA and open-records planning packet

Route this lane to `foia-open-records-planning` when the task is about public
records request planning, agency scope, request wording, exemptions, fee waivers,
tracking, appeals, or released-record intake.

- Sources: request letters, agency acknowledgments, response letters, released records, exemption logs, appeal letters, statutes, and agency portals.
- Claims: request scope, agency custodian, record series, date range, response status, exemption/redaction risk, fee status, appeal deadline, or released-record provenance.
- Events: request submitted, acknowledgment received, response received, release produced, denial issued, appeal filed, appeal resolved.
- Artifacts: request letter, acknowledgment, response package, release bundle, withholding log, appeal letter, and tracking note.
- Guardrails: request plans are not evidence; do not request or publish private-person details, minors, medical details, financial identifiers, or exempt records without lawful public-interest basis.

## Narrative-readiness review packet

Route this lane to `narrative-readiness-review` before public scripts, reports,
videos, timelines, Manim exports, or evidence boards.

- Sources: readiness reports, public-export audits, contradiction reports, source-independence reports, redaction audits, and source-ledger records.
- Claims: narrative-ready, needs caveat, source gap, privacy blocker, contradiction blocker, independence gap, or unsupported script point.
- Events: review completed, blocker resolved, public-export approved, claim excluded, caveat added.
- Guardrails: do not rewrite claim status automatically. Public narrative language must match source support, assertion type, confidence, contradiction status, and privacy review.

## Privacy-redaction audit packet

Route this lane to `privacy-redaction-audit` for private-person details, minors,
addresses, contact details, medical details, financial identifiers, weak
allegations, unsupported public claims, or redaction logs.

- Sources: redaction logs, public-export audits, source records, court/agency release notes, and internal review reports.
- Claims: redaction required, public export blocked, private-person detail removed, unsupported claim excluded, or replacement wording approved.
- Redactions: record ID, reason, source IDs/spans, replacement wording, review status, and public-export decision.
- Guardrails: public records can still contain private data. Keep sensitive details out of public notes where a locator and summary are enough.

## Source-independence audit packet

Route this lane to `source-independence-audit` for same-source chains, wire copy,
press-release repetition, shared authors/publishers, same docket/archive packets,
and corroboration independence review.

- Sources: source records, publisher metadata, wire bylines, press releases, docket packets, archive bundles, and source-independence reports.
- Claims: independence group, same-source chain, repeated copy, press-release origin, primary-record anchor, independent-source gap, or overstated corroboration.
- Events: source published, press release issued, wire story syndicated, correction published, independent source found.
- Guardrails: multiple citations do not equal corroboration when they trace to one source chain. Do not mark claims corroborated from dependent sources alone.
