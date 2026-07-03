# Skill API Operations

Operational workflows for planning, review, and core skill actions.

The operation names and safety tiers below are governed by
`crime_research_kit.sdk.operations`. Update the SDK catalog first, then refresh
this reference.

`tests/quality/governance/docs/test_sdk_operation_docs.py` drift-checks this
table and the operation detail headings against
`crime_research_kit.sdk.operations.list_operations()`.

Direct runtime exceptions are not SDK catalog entries. `crk-ledger report`,
`reportCase`, and MCP `run_report` remain direct until the evidence-board
report has explicit public/private filtering semantics.

## SDK Catalog Reference

| Skill API operation | SDK operation | Safety tier | Result envelope |
|---|---|---|---|
| `addSource` | `sources.add` | `staged_write` | `OperationResult` |
| `auditContradictions` | `review.audit_contradictions` | `staged_write` | `OperationResult` |
| `auditPrivacyRedactions` | `review.audit_privacy_redactions` | `staged_write` | `OperationResult` |
| `auditPublicExport` | `review.audit_public_export` | `public_export` | `OperationResult` |
| `auditSourceIndependence` | `review.audit_source_independence` | `staged_write` | `OperationResult` |
| `dedupeRecords` | `review.dedupe` | `staged_write` | `OperationResult` |
| `draftExtraction` | `extractions.draft` | `staged_write` | `OperationResult` |
| `exportAnalysisCharts` | `exports.analysis_charts` | `public_export` | `OperationResult` |
| `exportCaseCharts` | `exports.case_charts` | `public_export` | `OperationResult` |
| `exportManim` | `exports.manim` | `public_export` | `OperationResult` |
| `exportPeopleClusters` | `exports.people_clusters` | `public_export` | `OperationResult` |
| `exportTimeline` | `exports.timeline` | `public_export` | `OperationResult` |
| `importExtraction` | `extractions.import_reviewed` | `canonical_gated` | `OperationResult` |
| `indexTranscript` | `records.index_transcript` | `staged_write` | `OperationResult` |
| `ingestUrl` | `sources.ingest_url` | `staged_write` | `OperationResult` |
| `initCase` | `cases.create` | `staged_write` | `OperationResult` |
| `linkNames` | `names.link` | `staged_write` | `OperationResult` |
| `nerSuggest` | `extractions.ner_suggest` | `staged_write` | `OperationResult` |
| `planOpenRecords` | `records.plan_open_records` | `staged_write` | `OperationResult` |
| `planPublicRecords` | `records.plan_public_records` | `staged_write` | `OperationResult` |
| `preserveSource` | `sources.preserve` | `staged_write` | `OperationResult` |
| `resolveIdentities` | `review.resolve_identities` | `staged_write` | `OperationResult` |
| `reviewNarrativeReadiness` | `review.narrative_readiness` | `staged_write` | `OperationResult` |
| `validateCase` | `review.validate` | `read` | `OperationResult` |
