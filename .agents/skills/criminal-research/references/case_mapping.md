# TRCR Case Mapping For Criminal Research

Use existing TRCR ledgers. Criminal-research packets are interpretation layers over cited sources, not proof of identity, guilt, motive, or diagnosis.

## Sources

Prefer `source_type: academic`, `court_record`, `official_report`, `interview`, `memoir`, `book`, `documentary`, or `news_article` depending on the source. Grade academic, court, and official sources higher than sensational retellings when provenance is clear.

## Claims

Create one claim per analytical point:

- `<Source>` describes `<behavior>` as part of the offender's M.O.
- `<Expert/source>` characterizes `<pattern>` as `<academic or forensic concept>`.
- `<Event set>` shows `<source-backed pattern>` with caveats.
- `<Source>` reports `<victimology or target-selection factor>` without implying blame.

Use `assertion_type: expert_context` for scholarly or expert framing, `source_stated_fact` for observed source-stated behavior, and `lead_only` for hypotheses that need review.

## Events And Event Links

Use events for offense incidents, preparation, approach/contact, escalation, staging, disposal/recovery, confession/interview, court finding, expert report, or publication of analysis. Link entities to events only when the source directly supports the link.

## Relationships

Use conservative relationship labels such as `accused_by`, `charged_with`, `convicted_of`, `reported_by`, `interviewed_by`, `cited_by`, `pattern_compared_to`, or `expert_analysis_of`. Do not create hidden-control, motive, or guilt relationships from behavioral similarity.

## Notes And Privacy

Store diagnostic, private-person, minor-related, weak allegation, or suspect-comparison material with `public_export: false` until legal, privacy, contradiction, and narrative-readiness review are complete.
