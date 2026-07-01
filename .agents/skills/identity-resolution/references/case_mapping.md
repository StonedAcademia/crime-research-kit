# TRCR Case Mapping For Identity Resolution

Use existing TRCR ledgers. Do not add private identifiers just to improve matching.

## Candidate Reports

Run `resolve-identities` to write a review artifact under `staging/candidates/`. Treat it as internal analysis, not evidence. Evidence still belongs in source-backed records.

## Entities

Create or update entities only when the source supports the identity anchor:

- Add aliases that appear in public sources.
- Keep ambiguous entities `status: candidate`.
- Use `privacy_level: private_person`, `minor`, or `unknown` when public-export safety is not clear.
- Preserve old entity IDs unless a separate explicit merge task updates references safely.

## Claims

Use `claim_type: identity` for source-backed identity assertions:

- `<Name>` was listed as `<role>` in `<source>` on `<date>.`
- `<Alias>` was used for `<entity>` in `<source>.`
- `<Record A>` and `<Record B>` may refer to the same entity because `<public anchors>.`
- `<Record A>` and `<Record B>` do not appear to refer to the same entity because `<source-backed conflict>.`

Use `status: unverified` for candidates and `single_source` for one-source identity anchors.

## Relationships

Use relationship rows sparingly:

- `alias_of`
- `possibly_same_as`
- `not_same_as`
- `held_role_at`
- `named_in_record`
- `associated_with_identifier`

Keep `possibly_same_as` rows `public_export: false` until reviewed.

## Source Spans

Use `source_spans` for exact identity anchors: page, paragraph, docket item, accession, role table, byline, timestamp, or quote hint.

## Redactions

Add redaction rows when a source includes private-person identifiers that should not be exported: address, contact details, family details, school/workplace details, medical details, financial identifiers, or minor information.
