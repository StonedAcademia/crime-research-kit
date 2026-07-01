# Entity taxonomy

Use stable IDs. Do not use full names as IDs.
For the full controlled vocabulary reference, see `controlled_vocabularies.md`.

## entity_type

- `person`
- `organization`
- `group`
- `institution`
- `publication`
- `place_alias`
- `object`
- `vehicle`
- `document`
- `recording`
- `event_series`
- `other`

## role_tags for people

Use neutral tags:

- `founder`
- `leader`
- `member`
- `former_member`
- `witness`
- `eyewitness`
- `survivor`
- `victim`
- `relative`
- `journalist`
- `law_enforcement`
- `attorney`
- `judge`
- `researcher`
- `official`
- `charged_person`
- `convicted_person`
- `acquitted_person`
- `person_mentioned`

Only use legal/criminal labels when a source supports them.

## privacy_level

- `public_figure`
- `limited_purpose_public`
- `private_person`
- `minor`
- `not_applicable`
- `unknown`

Default to `private_person` when uncertain.

## living_status

- `living`
- `deceased`
- `unknown`
- `not_applicable`

Use `not_applicable` for non-person entities.

## public_export

Set `public_export: false` when:

- The person is a private living person with no clear public-interest reason.
- The person is a minor.
- The detail is contact/location-sensitive.
- The evidence is weak or disputed.
