# Controlled vocabularies

Use schema values when a field has an enum. For convention-only fields, keep the
values below unless a case note explains why a new value is needed.

## Source and evidence

- `source_type`: `news_article`, `eyewitness_account`, `court_record`, `government_record`, `official_report`, `interview`, `memoir`, `book`, `documentary`, `academic`, `archive`, `social_media_lead`, `other`
- `reliability_grade`: `A`, `B`, `C`, `D`, `X`
- `privacy_review`: `clear`, `needs_review`, `redact`, `exclude`
- `assertion_type`: `source_stated_fact`, `allegation`, `denial`, `court_finding`, `self_report`, `biography_claim`, `lead_only`, `expert_context`

`assertion_type` describes how the source presents the assertion. It does not
upgrade `status`, `confidence`, or public-readiness by itself.

## Entities

- `entity_type`: `person`, `organization`, `group`, `institution`, `publication`, `place_alias`, `object`, `vehicle`, `document`, `recording`, `event_series`, `other`
- `status`: `confirmed`, `candidate`, `excluded`, `merged`
- `privacy_level`: `public_figure`, `limited_purpose_public`, `private_person`, `minor`, `not_applicable`, `unknown`
- `living_status`: `living`, `deceased`, `unknown`, `not_applicable`
- `role_tags`: `founder`, `leader`, `member`, `former_member`, `witness`, `eyewitness`, `survivor`, `victim`, `relative`, `journalist`, `law_enforcement`, `attorney`, `judge`, `researcher`, `official`, `charged_person`, `convicted_person`, `acquitted_person`, `person_mentioned`

Only use legal or membership labels when a cited source uses that wording.

## Claims, relationships, and event links

- `claim_type`: `identity`, `timeline`, `relationship`, `event`, `location`, `motive`, `quote`, `background`, `legal`, `eyewitness`, `other`
- claim `status`: `verified`, `corroborated`, `single_source`, `disputed`, `unverified`, `false_or_retracted`, `excluded_from_public_script`
- relationship or event-link `status`: `verified`, `corroborated`, `single_source`, `disputed`, `unverified`, `excluded`
- `relationship_class`: `documented_successor`, `method_diffusion`, `personnel_bridge`, `narrative_inheritance`, `contested_overlap`, `hypothesis_requires_more_sources`

Phase 1 relationship and event-link conventions:

- Legal/court: `party_to`, `represented_by`, `presided_over_by`, `filed_by`, `accused_by`, `denied_by`, `ordered_by`, `appealed_by`, `witness_for`
- Identity resolution: `alias_of`, `possibly_same_as`, `not_same_as`, `held_role_at`, `named_in_record`, `associated_with_identifier`
- Source capture: `captured_from`, `archived_at`, `mirrored_by`, `derived_text_from`, `preserved_as`
- Contradiction review: `contradicts_claim`, `supports_claim`, `narrows_claim`, `corrects_claim`, `retracts_claim`, `denies_claim`
- Licensing/professional: `licensed_by`, `certified_by`, `disciplined_by`, `sanctioned_by`, `employed_as`, `credential_claimed_by`, `credential_disputed_by`
- Media/transcript: `interviewed_by`, `interviewed`, `said_in_interview`, `appeared_in`, `published_by`, `transcribed_by`
- Property/location: `owned_by`, `leased_by`, `transferred_to`, `permitted_by`, `inspected_by`, `located_in`, `operated_at`
- FOIA/open records: `requested_from`, `responded_to_by`, `released_by`, `withheld_by`, `appealed_to`
- Narrative readiness: `supports_public_point`, `requires_caveat`, `excluded_from_narrative`, `blocks_public_export`
- Privacy/redaction: `redacts_record`, `replaces_sensitive_detail`, `blocks_public_export`, `privacy_reviewed_by`
- Source independence: `copied_from`, `syndicated_from`, `derived_from_press_release`, `same_source_chain_as`, `independently_corroborates`

Use `co_mentioned_in_event` and `co_mentioned_with` only as lead language. Keep
those rows `unverified`, low confidence, and `public_export: false` until a
reviewed source directly supports a stronger relationship.

## Events

Use source-stated event types when needed. Prefer these Phase 1 conventions when
they fit:

- Legal/court: `case_filed`, `docket_entry`, `motion_filed`, `hearing`, `order_entered`, `judgment_entered`, `charge_filed`, `plea_entered`, `sentencing`, `appeal_filed`, `appeal_decided`, `settlement_entered`
- Source capture: `source_captured`, `archive_checked`, `source_preserved`, `source_updated`, `correction_published`, `retraction_published`
- Identity resolution: `identity_claim_recorded`, `alias_recorded`, `identity_conflict_recorded`, `entity_merge_reviewed`
- Contradiction review: `claim_disputed`, `claim_corrected`, `claim_retracted`, `claim_denied`, `court_finding_entered`
- Licensing/professional: `license_issued`, `license_status_changed`, `disciplinary_complaint_filed`, `board_order_entered`, `sanction_imposed`, `license_suspended`, `license_revoked`, `license_reinstated`, `credential_disputed`
- Media/transcript: `interview_recorded`, `media_published`, `hearing_held`, `statement_made`, `transcript_published`, `caption_corrected`, `followup_published`
- Property/location: `deed_transfer`, `permit_issued`, `inspection_completed`, `zoning_hearing`, `facility_opened`, `facility_closed`, `foreclosure_filed`, `property_sold`, `map_published`
- FOIA/open records: `records_request_planned`, `records_request_submitted`, `records_request_acknowledged`, `records_response_received`, `records_released`, `records_denied`, `appeal_filed`, `appeal_resolved`
- Narrative readiness: `narrative_review_completed`, `caveat_added`, `claim_excluded_from_narrative`, `readiness_blocker_resolved`
- Privacy/redaction: `privacy_audit_completed`, `redaction_applied`, `public_export_blocked`, `public_export_cleared`
- Source independence: `source_independence_review_completed`, `wire_story_syndicated`, `press_release_issued`, `independent_source_found`

## Source preservation

- `capture_method`: `ingest_url`, `manual_registration`, `archive_lookup`, `local_file`, `registered_source`
- `preservation_status`: `captured`, `registered_with_archive`, `metadata_only`, `missing_artifacts`

## Citation locators

Use `records/source_spans.jsonl` when a claim, event, relationship, event link,
quote, or artifact needs a precise locator. Link records to those rows with
`source_span_ids`:

```json
{
  "source_spans": [
    {
      "source_span_id": "SP...",
      "source_id": "S...",
      "locator_type": "page|paragraph|timestamp|line|section|url_fragment",
      "locator": {
        "page": 12,
        "quote_hint": "short locating phrase"
      },
      "exact_text": "Short support excerpt when needed",
      "notes": ""
    }
  ]
}
```

Keep quotes short and source-bound. A locator supports citation traceability; it
does not replace `source_ids`.

## Deduplication

Prefer stable IDs over display text. When merging duplicates, keep the surviving
ID, add aliases or notes, mark the replaced record `status: merged` when
retained, and record the reason in `notes`. Never silently rewrite existing IDs
that may already be referenced by claims, events, event links, relationships,
or exports.
