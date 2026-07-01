# Manim export spec

The CLI command:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-manim tc-c-kit/data/cases/<case_slug>
```

writes CSVs to:

```text
tc-c-kit/data/cases/<case_slug>/exports/manim/
```

## `events.csv`

Columns:

- `event_id`
- `title`
- `event_type`
- `start_date`
- `end_date`
- `date_precision`
- `place_ids`
- `entity_ids`
- `claim_ids`
- `source_ids`
- `confidence`
- `status`
- `public_export`

Use for timeline scenes.

## `relationships.csv`

Columns:

- `rel_id`
- `src_entity_id`
- `dst_entity_id`
- `relation_type`
- `relationship_class`
- `start_date`
- `end_date`
- `claim_ids`
- `source_ids`
- `confidence`
- `status`
- `public_export`

Use for directed network scenes.

## `event_links.csv`

Columns:

- `event_link_id`
- `entity_id`
- `event_id`
- `relation_type`
- `relationship_class`
- `basis`
- `claim_ids`
- `source_ids`
- `confidence`
- `status`
- `public_export`

Use for person/event edge scenes. Treat `co_mentioned_in_event` as an unverified research lead, not proof of participation or affiliation.

## `claims.csv`

Columns:

- `claim_id`
- `claim`
- `claim_type`
- `status`
- `confidence`
- `source_ids`
- `contradicts`
- `public_export`

Use for evidence boards and claim matrices.

## `people.csv`

Actually includes all public-safe entities, not only people. Filter on `entity_type` in Manim if needed.

Columns:

- `entity_id`
- `entity_type`
- `name`
- `display_name`
- `role_tags`
- `privacy_level`
- `public_export`
- `source_ids`

## `sources.csv`

Columns:

- `source_id`
- `title`
- `source_type`
- `publisher`
- `author`
- `date_published`
- `url`
- `archive_url`
- `reliability_grade`

Use for source ledger scenes.
