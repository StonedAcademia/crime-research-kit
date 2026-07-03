# SDK Operation Inventory

Date: 2026-07-03
Status: reviewed baseline for SDK extraction
Related spec: `docs/superpowers/specs/2026-07-03-sdk-target-shape.md`

## Scope

This inventory freezes the live operation baseline for the first SDK extraction
wave. It covers the current package metadata, operation wrappers, CLI commands,
MCP tools, app workflow service, and Skill API docs. Historical
`docs/superpowers` plans that still mention `src/case_builder`, `tcr.py`, or
zero-required-dependency assumptions are treated as archives unless an active
guide points at them.

## Distribution Baseline

| Surface | Current state | SDK decision |
| --- | --- | --- |
| Distribution name | `crime-research-kit` in `pyproject.toml` | Keep. Import namespace is separate. |
| Version at inventory time | `0.12.0` | Bump with implementation/release metadata once SDK modules land. |
| Console scripts | `cr-kit`, `crk-ledger`, `crk-mcp` | Keep stable; adapters should consume SDK/catalog behavior over time. |
| Published packages | `adapters*`, `core*`, `pipeline*` via setuptools discovery | Do not document these as SDK imports. Add `crime_research_kit*` and later decide whether to move or de-publicize internals. |
| Required dependencies | `jsonschema`, `pydantic`, `pydantic-settings`, `httpx`, `typer`, `jinja2` | SDK skeleton may rely on current required deps but must not add new required deps. |
| Optional capabilities | `agentic`, `llm`, `mcp`, `web-local`, `documents`, `retrieval`, `memory-local`, `governance` extras | SDK optional methods must raise actionable dependency errors rather than importing optional stacks at base import time. |

## Result And Envelope Drift

| Surface | Current shape | SDK target |
| --- | --- | --- |
| Ops result | `adapters.ops.result.OpResult` has `name`, `ok`, `data`, `errors`, `warnings`, `command`, `dry_run`, `skipped`, `returncode`, `stdout`, and `stderr`. | `OperationResult` should expose `ok`, `operation`, `case_ref`, `data`, `errors`, `warnings`, `created`, `updated`, `outputs`, `counts`, and optional `diagnostics`. |
| Skill API docs | Common response uses `operation`, `case_dir`, `created`, `updated`, `outputs`, `counts`, and `warnings`; error codes are documented separately. | SDK-004 must reconcile this with `OpResult` without making subprocess fields central. |
| CLI output | `cr-kit` prints JSON dicts from app handlers; `crk-ledger` dispatches command functions directly. | CLI should become an adapter over SDK results/catalog while preserving command output. |
| MCP output | Tool handlers return `OpResult.to_dict()` or `error_dict(message)`. | MCP should eventually return SDK/catalog-aligned envelopes and preserve existing tests. |

## Safety Tier Legend

| Tier | Meaning for catalog work |
| --- | --- |
| `read` | Does not write case data; must exclude `public_export=false` unless `include_private` is explicit. |
| `staged_write` | Writes staging, source-registry, generated reports, or lead-only artifacts; no canonical evidence import without gate. |
| `canonical_gated` | Writes canonical evidence records and requires explicit approval/confirm. |
| `public_export` | Generates public-facing exports, public-safe by default with explicit internal/private mode. |
| `internal_service` | Optional service/runtime capability, not base SDK behavior. |

## Case And Record Operations

| SDK candidate | Current operation/function | CLI surface | MCP tool | Skill API doc | Safety tier | SDK disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `client.cases.create` | `adapters.ops.casework.case.init_case` and `records.workspace.init_case` | `crk-ledger init-case` | - | `initCase` | `staged_write` | Stable SDK candidate. Creates workspace only, not evidence claims. |
| `case.info` | `adapters.ops.casework.case.case_info` | - | `case_info` | - | `read` | Stable SDK candidate; add docs/catalog entry because MCP already exposes it. |
| `client.cases.list` | `adapters.interfaces.mcp.context.list_case_slugs` | - | `list_cases` | - | `read` | Stable SDK candidate; current implementation is MCP-context-specific and must move behind context. |
| `case.records.list` | `adapters.ops.evidence.query.get_records` | - | `get_records` | - | `read` | Stable SDK candidate; default must filter private rows. |
| `case.records.source_text` | `adapters.ops.evidence.query.get_source_text` | - | `get_source_text` | - | `read` | Stable SDK candidate; default blocks private sources. |
| `case.reports.evidence_board` | `adapters.ops.casework.case.report`, `reports.case_outputs.report` | `crk-ledger report` | `run_report` | `reportCase` | `public_export` | SDK candidate, but renderer internals stay private. |

## Source And Intake Operations

| SDK candidate | Current operation/function | CLI surface | MCP tool | Skill API doc | Safety tier | SDK disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `case.sources.add` | `adapters.ops.casework.sources.add_source` and `records.workspace.add_source` | `crk-ledger add-source` | `add_source` | `addSource` | `staged_write` | Stable SDK candidate over source registry write. |
| `case.sources.ingest_url` | `adapters.ops.casework.sources.ingest_url` and `records.intake.web.ingest_url` | `crk-ledger ingest-url` | `ingest_url` | `ingestUrl` | `staged_write` | Stable SDK candidate; acquisition remains governed and local. |
| `case.sources.discover` | `adapters.ops.casework.sources.discover_sources` | `cr-kit discover-sources` | `discover_sources` | - | `staged_write` | Optional SDK capability; depends on SearXNG/http stack and writes lead-only candidates. |
| `case.sources.parse` | `adapters.ops.casework.sources.parse_source` | `cr-kit parse-source` | `parse_source` | - | `staged_write` | Optional SDK capability; dependency errors must be clear when document tools are absent. |
| `case.sources.ocr` | `adapters.ops.casework.sources.ocr_source` | `cr-kit ocr-source` | `ocr_source` | - | `staged_write` | Optional SDK capability; must not make OCR deps required. |
| `case.sources.preserve` | `adapters.ops.casework.sources.preserve_source` and `quality.preservation.preserve_source` | `crk-ledger preserve-source` | - | `preserveSource` | `staged_write` | Stable SDK candidate; updates preservation metadata/report, not evidence facts. |

## Extraction And Candidate Operations

| SDK candidate | Current operation/function | CLI surface | MCP tool | Skill API doc | Safety tier | SDK disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `case.extractions.draft` | `adapters.ops.casework.extraction.draft_extraction` and `records.extractions.draft_extraction` | `crk-ledger draft-extraction` | `draft_extraction` | `draftExtraction` | `staged_write` | Stable SDK candidate. |
| `case.extractions.list` | `adapters.ops.casework.extraction.list_packets` | - | `list_staged_packets` | - | `read` | Stable SDK candidate; should be documented/cataloged because MCP exposes it. |
| `case.extractions.read` | `adapters.ops.casework.extraction.read_packet` | - | - | - | `read` | SDK candidate; no current CLI/MCP command. |
| `case.extractions.save` | `adapters.ops.casework.extraction.save_packet` | - | `save_extraction_packet` | - | `staged_write` | Stable SDK candidate; lint and staged-write policy remain mandatory. |
| `case.extractions.import_reviewed` | `adapters.ops.casework.extraction.import_extraction` and `records.extractions.import_extraction` | `crk-ledger import-extraction` | `import_extraction` | `importExtraction` | `canonical_gated` | Stable SDK candidate; approval flag required at every surface. |
| `case.extractions.ner_suggest` | `records.intake.suggestions.ner_suggest` | `crk-ledger ner-suggest` | - | `nerSuggest` | `staged_write` | Candidate or review-planning method; output is lead-only and not evidence. |

## Planning, Names, And Review Operations

| SDK candidate | Current operation/function | CLI surface | MCP tool | Skill API doc | Safety tier | SDK disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `case.names.link` | `adapters.ops.evidence.query.link_names` and `records.names.command.link_names` | `crk-ledger link-names` | `link_names` | `linkNames` | `staged_write` | Stable SDK candidate; lead links stay private/unverified by default. |
| `case.records.plan_public_records` | `adapters.ops.casework.sources.plan_public_records` and `planning.public_records.plan_public_records` | `crk-ledger plan-public-records` | `plan_public_records` | `planPublicRecords` | `staged_write` | Stable SDK candidate. |
| `case.records.index_transcript` | `planning.transcripts.index_transcript` | `crk-ledger index-transcript` | - | `indexTranscript` | `staged_write` | Stable SDK candidate; report only, no canonical import. |
| `case.records.plan_open_records` | `planning.open_records.plan_open_records` | `crk-ledger plan-open-records` | - | `planOpenRecords` | `staged_write` | Stable SDK candidate; planning artifact only. |
| `case.review.validate` | `adapters.ops.casework.case.validate` and `records.validation.validate` | `crk-ledger validate` | - | `validateCase` | `read` | Stable SDK candidate; may generate validation diagnostics. |
| `case.review.dedupe` | `quality.dedupe.dedupe` | `crk-ledger dedupe` | - | `dedupeRecords` | `staged_write` | Stable SDK candidate; writes candidate report, no merge/delete. |
| `case.review.resolve_identities` | `quality.identity.resolve_identities` | `crk-ledger resolve-identities` | - | `resolveIdentities` | `staged_write` | Stable SDK candidate; no merge/delete. |
| `case.review.audit_contradictions` | `quality.contradictions.audit_contradictions` | `crk-ledger audit-contradictions` | - | `auditContradictions` | `staged_write` | Stable SDK candidate; review report only. |
| `case.review.narrative_readiness` | `quality.safety.readiness.review_narrative_readiness` | `crk-ledger review-narrative-readiness` | - | `reviewNarrativeReadiness` | `staged_write` | Stable SDK candidate; fail-closed option belongs in request model. |
| `case.review.audit_privacy_redactions` | `quality.safety.privacy.audit_privacy_redactions` | `crk-ledger audit-privacy-redactions` | - | `auditPrivacyRedactions` | `staged_write` | Stable SDK candidate. |
| `case.review.audit_public_export` | `quality.safety.public_export.audit_public_export` | `crk-ledger audit-public-export` | - | `auditPublicExport` | `public_export` | Stable SDK candidate; public-safety gate for exports. |
| `case.review.audit_source_independence` | `quality.safety.source_independence.source_independence` | `crk-ledger audit-source-independence`, alias `source-independence` | - | `auditSourceIndependence` | `staged_write` | Stable SDK candidate; catalog should record CLI alias. |

## Export Operations

| SDK candidate | Current operation/function | CLI surface | MCP tool | Skill API doc | Safety tier | SDK disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `case.exports.manim` | `adapters.ops.evidence.exports.export_manim`, `reports.case_outputs.export_manim` | `crk-ledger export-manim` | `export_manim` | `exportManim` | `public_export` | Stable SDK candidate; public-safe by default. |
| `client.exports.timeline` | `adapters.ops.evidence.exports.export_timeline`, `reports.timeline.export_timeline` | `crk-ledger export-timeline` | - | `exportTimeline` | `public_export` | Stable SDK candidate; cross-case scope belongs on top-level client. |
| `case.exports.case_charts` | `adapters.ops.evidence.exports.export_case_charts`, `reports.case_charts.command.export_case_charts` | `crk-ledger export-case-charts` | `export_case_charts` | `exportCaseCharts` | `public_export` | Stable SDK candidate. |
| `case.exports.analysis_charts` | `adapters.ops.evidence.exports.export_analysis_charts`, `reports.analysis.command.entry.export_analysis_charts` | `crk-ledger export-analysis-charts` | `export_analysis_charts` | `exportAnalysisCharts` | `public_export` | Stable SDK candidate. |
| `case.exports.people_clusters` | `reports.clusters.command.export_people_clusters` | `crk-ledger export-people-clusters` | - | `exportPeopleClusters` | `public_export` | Stable SDK candidate with optional graph-analysis deps. |

## Workflow And Optional Service Operations

| SDK candidate | Current operation/function | CLI surface | MCP tool | Skill API doc | Safety tier | SDK disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `client.workflows.plan` | `pipeline.app.service.run_case_builder` | `cr-kit plan` | - | - | `internal_service` | Stable workflow facade candidate; app service remains orchestration boundary, graph internals stay private. |
| `client.workflows.resume` | `pipeline.app.service.resume_case_builder` | `cr-kit resume` | - | - | `internal_service` | Stable workflow facade candidate; approvals for packet/export gates stay explicit. |
| `case.retrieval.index` | `adapters.ops.evidence.query.index_case` | `cr-kit index-case` | - | - | `internal_service` | Optional capability, not base SDK. |
| `case.retrieval.query` | `adapters.ops.evidence.query.query_case` | `cr-kit query-case` | `query_case` | - | `internal_service` | Optional capability; read semantics must honor `include_private`. |
| `case.memory.remember_research_actions` | `core.memory.remember_research_actions` | `cr-kit remember-research-actions` | - | - | `internal_service` | Optional capability or adapter-only command; not part of first public SDK core. |

## Historical Drift Findings

| Finding | Evidence | Decision |
| --- | --- | --- |
| Historical `src/case_builder` paths remain in archived planning docs. | Multiple `docs/superpowers/2026-07-01*` and `2026-07-02*` plans/specs still mention `src/case_builder` and `case_builder.*`. | Treat as archives. New SDK work must use the live top-level `src/adapters`, `src/core`, and `src/pipeline` layout until private runtime migration. |
| Historical `tcr.py` references remain in archived specs/plans. | Older superpowers specs mention `tcr.py`; active package metadata exposes `crk-ledger`. | Do not recreate `tcr.py` wrappers or preserve `tcr.py` as an SDK contract. |
| The zero-required-dependency assumption is stale. | `pyproject.toml` has required dependencies and the changelog says the core package is no longer stdlib-only. | SDK skeleton must not add new required deps, but it can use current required deps such as pydantic where appropriate. |

## First Catalog Seed

The initial `OperationSpec` catalog should prioritize these stable SDK names:

- `cases.create`, `cases.list`, `case.info`
- `records.list`, `records.source_text`, `records.plan_public_records`,
  `records.index_transcript`, `records.plan_open_records`
- `sources.add`, `sources.ingest_url`, `sources.discover`, `sources.parse`,
  `sources.ocr`, `sources.preserve`
- `extractions.draft`, `extractions.list`, `extractions.read`,
  `extractions.save`, `extractions.import_reviewed`,
  `extractions.ner_suggest`
- `names.link`
- `review.validate`, `review.dedupe`, `review.resolve_identities`,
  `review.audit_contradictions`, `review.narrative_readiness`,
  `review.audit_privacy_redactions`, `review.audit_public_export`,
  `review.audit_source_independence`
- `exports.manim`, `exports.timeline`, `exports.case_charts`,
  `exports.analysis_charts`, `exports.people_clusters`
- `workflows.plan`, `workflows.resume`

The catalog should also carry CLI command names, MCP tool names, Skill API
camelCase names, future HTTP routes where documented, safety tier, side effects,
and explicit `not_sdk` exemptions for adapter-only or optional service commands.
