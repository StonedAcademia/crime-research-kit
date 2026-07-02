# CRK Case Mapping For Media Transcript Intelligence

Use existing CRK ledgers. Media claims need timestamp or line locators whenever possible.

## Sources

Use `source_type: interview`, `documentary`, `official_report`, `news_article`, or `other` depending on the source. Preserve original URL, archive URL, transcript source, and capture metadata.

## Entities

Create entities for speakers, interviewers, subjects, publishers, producers, transcript providers, and organizations named in the media.

## Claims

Create one claim per specific statement:

- `<Speaker>` said `<statement>` at `<timestamp>`.
- `<Speaker>` self-reported `<event>` in `<interview>`.
- `<Narrator>` described `<context>` in `<documentary>`.
- `<Transcript>` identifies `<speaker>` as saying `<quote>`.

Use `claim_type: quote`, `eyewitness`, `timeline`, `relationship`, or `background` as appropriate.

## Quotes

Use `quotes` for short exact excerpts only. Link quotes to `source_id` and `source_span_ids`.

## Source Spans

Use `locator_type: timestamp`, `line`, `section`, or `quote_offset`. Include speaker, line, clip URL, episode, or timestamp when available.

## Events

Use events for interview recorded, broadcast published, hearing held, statement made, correction issued, or transcript published.

## Relationships

Use source-stated relationships such as `interviewed_by`, `interviewed`, `said_in_interview`, `appeared_in`, `published_by`, and `transcribed_by`.
