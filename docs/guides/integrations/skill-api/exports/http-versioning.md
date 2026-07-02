# HTTP Mapping And Versioning

## Future HTTP Mapping

If this CLI is wrapped by an HTTP API, use these stable operation routes:

| Method | Path | Operation |
|---|---|---|
| `POST` | `/v1/cases` | `initCase` |
| `POST` | `/v1/cases/{case_slug}/sources` | `addSource` |
| `POST` | `/v1/cases/{case_slug}/sources:ingest-url` | `ingestUrl` |
| `POST` | `/v1/cases/{case_slug}/extractions:draft` | `draftExtraction` |
| `POST` | `/v1/cases/{case_slug}/extractions:import` | `importExtraction` |
| `POST` | `/v1/cases/{case_slug}/candidates:ner-suggest` | `nerSuggest` |
| `POST` | `/v1/cases/{case_slug}/links:names` | `linkNames` |
| `POST` | `/v1/cases/{case_slug}:validate` | `validateCase` |
| `POST` | `/v1/cases/{case_slug}:report` | `reportCase` |
| `POST` | `/v1/cases/{case_slug}/exports:manim` | `exportManim` |
| `POST` | `/v1/cases/{case_slug}:dedupe` | `dedupeRecords` |
| `POST` | `/v1/cases/{case_slug}:audit-public-export` | `auditPublicExport` |
| `POST` | `/v1/cases/{case_slug}:audit-source-independence` | `auditSourceIndependence` |
| `POST` | `/v1/cases:export-timeline` | `exportTimeline` |
| `POST` | `/v1/cases/{case_slug}/exports:charts` | `exportCaseCharts` |
| `POST` | `/v1/cases/{case_slug}/exports:analysis-charts` | `exportAnalysisCharts` |
| `POST` | `/v1/cases/{case_slug}/exports:people-clusters` | `exportPeopleClusters` |

The HTTP wrapper must preserve local safety defaults, especially explicit
opt-in for private records.

## Versioning

Use semantic versions for the skill API contract:

- `0.x`: draft/local-only; breaking changes allowed with docs updates.
- `1.0`: stable record schemas, stable operation names, and stable response envelope.

Breaking changes include:

- renaming operation names
- removing request fields
- changing default privacy/public-export behavior
- changing CSV column names
- changing record ID generation semantics

Non-breaking changes include:

- adding optional request fields
- adding new output files
- adding new record fields under schemas that allow additional properties
- adding new validation warnings

## Open Questions

- Whether `review-links` should become a first-class operation for promoting, excluding, or annotating co-mention links.
- Whether stronger source-stated relationship upgrades should be handled by `importExtraction` options or a separate review operation.
- Whether future service wrappers should expose raw source text or keep it local-only.
