# CRK SDK Target Shape And Inventory

Date: 2026-07-03
Status: proposed target shape, planning package
Scope: `src/`, `pyproject.toml`, `docs/guides/integrations/skill-api/`, `docs/guides/architecture/`, `tests/runtime/`, `tests/quality/governance/`

## Goal

Turn the existing SDK-like pieces into a proper Python SDK without inheriting
legacy weight from the current app decomposition. The SDK should be a clean
public package surface for case, source, extraction, review, export, and
workflow operations. CLI, MCP, and future HTTP surfaces should adapt the SDK;
the SDK should not adapt those interfaces.

This is a pre-1.0 cleanup. It may deliberately break import paths that were
never declared public. Preserve the command-line and ledger behavior that
researchers already use, but do not preserve accidental Python imports such as
top-level `adapters`, `core`, or `pipeline` as compatibility promises.

## Namespace Decision

Decision: the public Python SDK namespace is `crime_research_kit.sdk`.

The distribution name remains `crime-research-kit`, and the existing console
scripts remain `cr-kit`, `crk-ledger`, and `crk-mcp`. Do not add
`case_builder.*` aliases, and do not document top-level `adapters`, `core`, or
`pipeline` as public SDK imports. Those packages may remain implementation
layout during the migration, but they are not compatibility promises for SDK
consumers.

## Current Inventory

| Surface | Current files | What exists now | Target disposition |
| --- | --- | --- | --- |
| Distribution | `pyproject.toml` | Distribution name is `crime-research-kit`; console scripts are `cr-kit`, `crk-ledger`, and `crk-mcp`; packages exported today are top-level `adapters*`, `core*`, and `pipeline*`. | Keep console scripts. Add a real public import namespace, preferably `crime_research_kit`. Stop treating top-level implementation packages as public SDK surface. |
| Ledger contract | `docs/guides/skill-api-spec.md`, `docs/guides/integrations/skill-api/*` | Machine-facing operation docs exist, but the documented envelope does not exactly match `OpResult`. | Make the SDK operation catalog the source for operation names, safety tiers, error codes, and generated reference docs. |
| Canonical data | `data/cases/<slug>/records/*.jsonl`, `docs/schemas/*`, `src/core/models/*` | JSONL ledger and schemas are canonical; pydantic record models mirror schemas. | SDK reads and writes through typed operation methods only. JSONL helpers stay internal. |
| Core helpers | `src/core/casefile.py`, `src/core/config.py`, `src/core/lanes/*`, `src/core/memory/*` | Case path resolution, record IO, settings, lane registry, and memory are mixed under a top-level package. | Split into public model/config types and private runtime helpers under the new namespace. Do not expose raw file-mutating helpers as SDK primitives. |
| Result envelope | `src/adapters/ops/result.py` | `OpResult` is a pydantic model with `ok`, `data`, `errors`, `warnings`, `command`, `dry_run`, `stdout`, and `stderr`. | Promote to `OperationResult` with stable fields aligned to Skill API docs; keep command/debug fields internal or explicitly marked diagnostic. |
| Runner/transport | `src/adapters/ops/runner.py` | `CrkRunner` shells through `python -m adapters.interfaces.cli` and returns `OpResult`; dry run is command planning. | Replace as the default SDK abstraction with a transport interface. Keep subprocess execution as an internal transport only where direct Python operation code is not yet clean. |
| Safety policy | `src/adapters/ops/safety/policy.py` | Staged-write enforcement, public filtering, automation defaults, LLM egress logging, and guilt-label lint exist. | Keep as a first-class SDK safety layer. Safety tier belongs in the operation catalog, not scattered across wrappers. |
| Case/source ops | `src/adapters/ops/casework/*` | Lifecycle, source intake, extraction packets, name linking, validation, and planning exist. Some operations wrap CLI, others call Python directly. | Organize behind `client.cases`, `case.sources`, `case.extractions`, and `case.records`; make transport choice invisible to callers. |
| Evidence ops | `src/adapters/ops/evidence/*` | Query, review audits, exports, report/chart builders, safety audits, and ledger report helpers exist. | Expose stable methods for records, review, and exports. Keep report renderer internals private. |
| Optional IO | `src/adapters/io/*` | SearXNG acquisition, Docling/OCR parsing, and Qdrant retrieval are optional and lazily imported. | Expose as optional SDK capabilities with clear dependency errors; do not make optional services part of the base client contract. |
| CLI interfaces | `src/adapters/interfaces/cli/*`, `src/cli.py` | Typer apps define the researcher CLI and case-builder CLI. Handlers call ops and app service. | CLI becomes an adapter over SDK clients and operation catalog. It should not own operation behavior or payload shapes. |
| MCP interface | `src/adapters/interfaces/mcp/*` | FastMCP server, context, tools, resources, and prompts call ops directly. Tool tiers are manually defined. | MCP tool registration should be generated or driven from operation catalog metadata plus explicit prompt/resource definitions. |
| LLM helpers | `src/adapters/interfaces/llm/*` | Local Ollama provider and bounded packet/readiness helpers exist. | Keep optional and local-first. SDK exposes LLM-assisted workflow options only as explicit opt-in fields. |
| App service | `src/pipeline/app/service.py` | `run_case_builder` and `resume_case_builder` choose runner, checkpoint mode, model factory, and return serializable state. | Keep app service as workflow orchestration. It consumes `WorkflowClient`; it is not the SDK. |
| Graph runtime | `src/pipeline/graph/*` | Sequential and LangGraph paths share nodes, review gates, and checkpointing. | Keep private runtime. SDK exposes workflow methods and resumable run state, not graph nodes. |
| Tests | `tests/runtime/*`, `tests/quality/governance/*` | Good coverage exists for result, policy, records, MCP tools, graph gates, resume, schemas, packaging, and docs drift. | Add SDK contract tests and generated-operation parity tests so CLI/MCP/docs cannot drift from SDK metadata. |
| Historical plans | `docs/superpowers/*` | Several older plans still mention `src/case_builder`, `tcr.py`, and older zero-dependency assumptions. | Treat as archives. New work must target the live top-level `src/` layout and current dependency policy. |

## Legacy Weight To Drop

| Do not inherit | Why | Target decision |
| --- | --- | --- |
| Top-level `adapters`, `core`, `pipeline` as public imports | They are implementation layout, not an SDK namespace. | Public import surface starts under `crime_research_kit`. |
| Compatibility shims for `case_builder.*` | Those paths are already historical and would make the new SDK carry stale shape. | No `case_builder` SDK aliases. Historical docs stay archived unless actively migrated. |
| CLI-first operation design | CLI flags are useful UX, but not the best SDK contract. | SDK defines typed methods; CLI maps flags into those methods. |
| Subprocess runner as the SDK identity | It preserves behavior but leaks implementation details into every caller. | Transport is private. Direct Python operations are preferred; subprocess remains a bounded fallback. |
| Duplicated operation lists | Operation names appear in docs, CLI, MCP, tests, and HTTP mapping. | One operation catalog feeds docs and adapters. |
| Multiple error envelopes | `OpResult`, `SystemExit`, MCP `error_dict`, and raw exceptions all exist. | Stable `OperationResult` plus typed `CrkError`/error codes at SDK boundary. |
| Interface-specific safety gates | MCP, graph, and ops all describe gates separately. | Safety tier is operation metadata; adapters render it. |
| Raw dicts as the public API everywhere | They are easy internally but weak for external users. | Public request/result objects use pydantic models; `model_dump()` remains available. |
| Optional service assumptions | Retrieval, OCR, MCP, LangGraph, and LLM extras are useful but not base SDK. | Optional capabilities raise clear dependency errors and remain isolated. |

## Target Package Shape

```text
src/crime_research_kit/
  __init__.py
  sdk/
    __init__.py
    client.py          # CrkClient and CaseClient entrypoints
    context.py         # CrkContext: repo root, cases root, settings, transport
    results.py         # OperationResult, OperationWarning, diagnostic metadata
    errors.py          # CrkError, error codes, dependency/safety/input errors
    operations.py      # OperationSpec catalog and safety tiers
    cases.py           # case lifecycle and record reads
    sources.py         # source registration, ingest, preserve, discovery
    extractions.py     # draft, stage, read, import with explicit approval
    review.py          # validation and deterministic audits
    exports.py         # public-safe exports
    workflows.py       # plan/resume workflow facade
    requests/          # strict request models keyed by OperationSpec
    examples/          # importable example recipes, not a runtime layer
  models/
    records/           # public record models already mirrored from schemas
    workflow.py        # public workflow request/result models
  _runtime/
    ledger/            # private JSONL helpers and legacy command adapters
    ops/               # private operation implementations while migrating
    interfaces/        # CLI/MCP adapters after they move under namespace
    pipeline/          # private graph runtime
```

The target shape separates public SDK from runtime implementation. A caller
should be able to write:

```python
from crime_research_kit.sdk import CrkClient, CrkContext

client = CrkClient(CrkContext(cases_root="data/cases"))
case = client.case("harbor_study_circle")
sources = case.records.list("sources")
packet = case.extractions.draft("SDEMO0001")
```

and never import `adapters`, `core`, `pipeline`, `CrkRunner`, or MCP/CLI modules.

## Public SDK Objects

| Object | Responsibility | Notes |
| --- | --- | --- |
| `CrkContext` | Runtime roots, privacy defaults, resolved settings, and transport selection. | Created at process boundaries or by external SDK users. |
| `CrkClient` | Top-level entrypoint for cases, global exports, and workflows. | No direct file IO methods. |
| `CaseClient` | Case-rooted operations so callers stop passing `case_dir` repeatedly. | Slug/path resolution is explicit and safe. |
| `OperationSpec` | Name, request model, result model, safety tier, side effects, CLI/MCP/HTTP mapping. | Single source for adapters and docs. |
| `OperationRequest` | Strict request payload base for catalog `request_model` names. | Pydantic models reject unknown fields and are resolved through `crime_research_kit.sdk.requests`. |
| `OperationResult` | Stable result envelope with `ok`, `operation`, `case_ref`, `data`, `warnings`, `errors`, `created`, `updated`, `outputs`, `counts`. | Diagnostics such as commands/stdout are present only when requested. |
| `CrkError` | Typed exception carrying error code and operation context. | SDK methods may return results or raise based on client mode; default should be result-returning for parity with current ops. |
| `WorkflowClient` | `plan`, `resume`, `status`, and run-state helpers. | Owns app-layer orchestration facade, not graph internals. |
| `crime_research_kit.sdk.examples` | Importable examples for common SDK calls. | Documentation and smoke-test recipes only; not a runtime layer. |

## Operation Taxonomy

| Domain | SDK surface | Current source | Safety tier |
| --- | --- | --- | --- |
| Cases | `client.cases.create`, `case.info`, `client.cases.list` | `casework.case`, MCP context | read or staged workspace |
| Records | `case.records.list`, `case.records.source_text` | `evidence.query`, `casefile` | read, private opt-in |
| Sources | `case.sources.add`, `ingest_url`, `preserve`, `discover`, `parse`, `ocr` | `casework.sources`, `adapters.io` | staged/source registry |
| Extractions | `case.extractions.draft`, `list`, `read`, `save`, `import_reviewed` | `casework.extraction` | staged or gated canonical |
| Names/planning | `case.names.link`, `case.records.plan_public_records`, `plan_open_records`, `index_transcript` | `casework.records.*` | staged/private leads |
| Validation/review | `case.review.validate`, `dedupe`, `resolve_identities`, `audit_*`, `readiness` | `records.validation`, `evidence.quality`, `evidence.review` | read plus generated reports |
| Exports | `case.exports.manim`, `case.exports.charts`, `client.exports.timeline` | `evidence.exports`, reports | public-safe default, private opt-in |
| Workflow | `client.workflows.plan`, `resume` | `pipeline.app.service` | gated by packet/export review |
| Optional services | `case.discovery`, `case.retrieval`, `case.memory` or explicit capability modules | `adapters.io`, `core.memory` | optional, not evidence |

## Optional Capability Matrix

| Capability | Current sources | Dependency boundary | SDK rule |
| --- | --- | --- | --- |
| Discovery / SearXNG | `adapters.io.acquisition`, `cr-kit discover-sources`, MCP `discover_sources` | `web-local` behavior plus configured `CRK_SEARXNG_URL` | Expose as optional source-discovery capability; base SDK import must not require a running service. |
| Documents / Docling | `adapters.io.parsing.parse_source`, `cr-kit parse-source`, MCP `parse_source` | `documents` extra | Raise an actionable dependency error when unavailable. |
| OCR | `adapters.io.parsing.ocr_source`, `cr-kit ocr-source`, MCP `ocr_source` | `documents` extra plus OCR binaries | Raise dependency/tooling errors without making OCR part of base install. |
| Retrieval / Qdrant-LlamaIndex | `adapters.io.retrieval`, `cr-kit index-case`, `cr-kit query-case`, MCP `query_case` | `retrieval` extra plus configured Qdrant | Optional capability; reads must still default to public-safe records. |
| Memory / Mem0 | `core.memory`, `cr-kit remember-research-actions` | `memory-local` extra and local provider settings | Not part of first public SDK core; if exposed later, it must be explicit and non-evidence. |
| LLM helpers | `adapters.interfaces.llm`, graph model factory | `llm` extra and local model provider | Opt-in only; local-first and egress-audited. |
| MCP server | `adapters.interfaces.mcp` | `mcp` extra | Adapter over SDK/catalog, not required for SDK import. |
| LangGraph workflows | `pipeline.graph`, checkpoint persistence | `agentic` extra | App/runtime implementation detail behind workflow facade. |

## App Layer Target

The app layer remains a use-case boundary, not a public SDK boundary.

- `pipeline/app/service.py` should keep only workflow concerns: runner choice,
  checkpointing, model factory wiring, and serializable run state.
- It should consume `WorkflowClient` or the same operation catalog-backed
  services the SDK exposes.
- It should not instantiate deep settings except at the explicit process
  boundary, parse CLI flags, register MCP tools, infer operation metadata, or
  duplicate safety tiers.
- Graph nodes stay private and call SDK/runtime operations. External users get
  `client.workflows.plan()` and `client.workflows.resume()`.

## Migration Stance

This is not a "wrap the current tree and call it done" migration. The existing
tree is allowed to remain as implementation while the SDK lands, but the public
contract must be new and narrow:

1. Keep `cr-kit`, `crk-ledger`, and `crk-mcp` as operator surfaces.
2. Add `crime_research_kit.sdk` as the Python API.
3. Move operation declarations into `OperationSpec`.
4. Repoint CLI, MCP, and app workflow to SDK/catalog behavior.
5. Once tests prove parity, move private implementation under
   `crime_research_kit._runtime` or otherwise mark top-level packages as
   non-public until they can be removed from package discovery.

## Acceptance Criteria

- A new user can import `crime_research_kit.sdk` and perform case-scoped read,
  source, extraction, review, export, and workflow operations without knowing
  about CLI modules.
- Operation names, safety tiers, request fields, and response fields are defined
  once and reused by docs, CLI, MCP, and tests.
- Public reads exclude `public_export: false` by default everywhere.
- Canonical import still requires explicit human approval and a confirm/approval
  field at every surface.
- Optional dependencies remain optional with actionable dependency errors.
- No `case_builder.*` or top-level `adapters/core/pipeline` path becomes a
  backwards-compatibility promise for SDK consumers.
- Existing command-line workflows continue to work.

## Out Of Scope

- Redesigning the JSONL ledger schema.
- Changing public safety semantics.
- Adding an HTTP server.
- Replacing MCP prompts/resources.
- Rewriting report rendering before the SDK boundary is stable.
- Maintaining legacy Python import compatibility for historical `case_builder`
  or top-level implementation paths.
