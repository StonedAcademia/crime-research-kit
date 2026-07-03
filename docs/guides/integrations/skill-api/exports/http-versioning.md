# HTTP Mapping And Versioning

## Future HTTP Mapping

SDK-021 does not add an HTTP server, ASGI app, or remote transport. It only
records future HTTP route metadata on SDK operation specs so later service
wrappers can bind routes without inventing a parallel operation list.

Future HTTP wrappers must read route metadata from
`crime_research_kit.sdk.operations` (`http_route_bindings()` or
`OperationSpec.http_route` via `list_operations()`), not maintain a separate
hand-written registry. The table below is the current catalog view of promoted
routes: method and path come from `http_route`, and operation is the stable
Skill API operation name.

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
| `POST` | `/v1/cases/{case_slug}/exports:manim` | `exportManim` |
| `POST` | `/v1/cases/{case_slug}:dedupe` | `dedupeRecords` |
| `POST` | `/v1/cases/{case_slug}:audit-public-export` | `auditPublicExport` |
| `POST` | `/v1/cases/{case_slug}:audit-source-independence` | `auditSourceIndependence` |
| `POST` | `/v1/cases:export-timeline` | `exportTimeline` |
| `POST` | `/v1/cases/{case_slug}/exports:charts` | `exportCaseCharts` |
| `POST` | `/v1/cases/{case_slug}/exports:analysis-charts` | `exportAnalysisCharts` |
| `POST` | `/v1/cases/{case_slug}/exports:people-clusters` | `exportPeopleClusters` |

Any future HTTP wrapper must preserve the SDK operation semantics in this
mapping: method and path identify the route, operation identifies the cataloged
Skill API operation, local safety defaults remain in force, and private records
still require explicit opt-in.

The evidence-board `reportCase` route is deferred until that report has
explicit public/private filtering semantics and a public SDK operation.

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
