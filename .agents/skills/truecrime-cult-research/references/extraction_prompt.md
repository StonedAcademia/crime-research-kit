# Extraction prompt for Codex/LLM use

Use this prompt after a source has been ingested and a draft extraction packet exists.

```text
Use the truecrime-cult-research extraction rules.
Read the source text at [TEXT_PATH] and fill [EXTRACTION_JSON_PATH].
Extract only what the source directly supports.
Do not infer guilt, group membership, motive, or relationships unless the source states them.
Treat eyewitness statements as claims with speaker, account type, and source ID.
Use neutral labels. Redact private-person details and minors by default.
Every entity/event/event_link/claim/relationship/quote must include source_ids containing [SOURCE_ID].
Use references/controlled_vocabularies.md for statuses, assertion_type, privacy, and relationship_class.
Add source_spans when a claim/event/relationship/event_link/quote needs page, paragraph, timestamp, line, or section locators.
When uncertain, use status=unverified or notes explaining the uncertainty.
```

## Field expectations

### Entities

Add people, organizations, groups, publications, objects, documents, vehicles, and other relevant named things.

### Claims

A claim is any assertion a public output might repeat. Break compound claims into smaller claims.
Use `assertion_type` to preserve how the source frames the statement, such as
`source_stated_fact`, `allegation`, `denial`, `court_finding`, `self_report`,
`biography_claim`, `lead_only`, or `expert_context`.

Bad:

```text
The leader founded the group in 1965 and used coercive control.
```

Better:

```text
C001: The source states the group began meeting in 1965.
C002: The source states [named person] led the early meetings.
C003: The source alleges members were isolated from family.
```

### Events

Use approximate dates when needed:

- `1965-00-00` for year-only if your tooling supports it, or use `date_precision: year`.
- Otherwise use ISO date plus `date_precision`.

### Relationships

Capture relation type and whether it is source-stated, inferred, alleged, or disputed.

Examples:

- `founded`
- `led`
- `joined`
- `recruited`
- `witnessed`
- `reported_to`
- `family_of`
- `employed_by`
- `member_of`
- `accused_by`
- `charged_with`
- `convicted_of`
- `denied_by`

### Event links

Use `event_links` for entity-to-event edges that should stay separate from event rows. Co-mention links must use neutral language such as `co_mentioned_in_event`, `status: unverified`, low confidence, and `public_export: false` unless a reviewed source explicitly supports stronger wording.

### Source spans

Use `records/source_spans.jsonl` for precise citation locators. Keep each span
tied to `source_span_id`, `source_id`, `locator_type`, and structured
`locator`; add `source_span_ids` to claims/events/relationships/event links,
quotes, or artifacts when needed. Do not use a locator as a substitute for
`source_ids`.

### Topic-specific templates

Use `topic_extraction_templates.md` for baseline packets. Route primarily
corporate, organizational, financial, board, ownership, investment, bankruptcy,
or transaction work to `corporate-financial-records`. Route schools, degrees,
training, credentials, academic appointments, alumni claims, and institution
affiliations to `educational-path-records`. Route missing-person candidates and
status updates to `missing-persons-case`. Route event/evidence geography and
map packets to `geographical-location-intelligence`.

## Output rule

Do not change existing IDs unless they are clearly placeholders. Add notes for unresolved duplicates.
