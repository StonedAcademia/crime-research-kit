# SDK

`crime_research_kit.sdk` is the stable Python SDK namespace.

Current surface:

- `CrkContext` carries caller-provided roots, privacy defaults, resolved
  settings, metadata, and transport mode.
- `CrkClient` is the top-level SDK entrypoint.
- `CaseClient` is a case-scoped handle that stores the resolved case context.
- `CasesClient` and `CaseRecordsClient` expose case listing, case info, public
  record reads, source-text reads, and public-record planning.
- `CaseRetrievalClient` exposes local retrieval query wrappers.
- `CaseSourcesClient` exposes source registration, URL ingestion,
  preservation, discovery, parsing, and OCR wrappers.
- `CaseExtractionsClient` exposes staged extraction draft, list, read, save,
  reviewed import, and lead-only NER suggestion wrappers.
- `CaseNamesClient` exposes lead-only name-linking wrappers.
- `CaseReviewClient` exposes validation, duplicate/identity review, and safety
  audit wrappers.
- `CaseExportsClient` exposes Manim, case-chart, analysis-chart, and
  people-cluster export wrappers.
- `ExportsClient` exposes top-level export wrappers such as the cross-case
  timeline export.
- `WorkflowClient` exposes case-builder plan and resume workflow wrappers.
- `WorkflowPlanRequest` and `WorkflowResumeRequest` define workflow request
  fields without exposing graph nodes.
- `crime_research_kit.sdk.examples` provides importable recipes for common
  integrator flows.
- `TransportMode` records whether clients should use automatic, direct, or
  subprocess-backed runtime access.
- `OperationResult` and `OperationWarning` define the stable SDK result
  envelope.
- `CrkError` and related subclasses define stable SDK error codes.
- `SafetyTier` and `OperationSpec` describe public operation wrappers before
  they are wired.
- `list_operations()`, `get_operation()`, and `operations_by_domain()` expose
  the current public operation specification catalog.

The operation catalog remains the source of operation metadata as wrappers are
promoted into the SDK.

Only this `crime_research_kit.sdk` package is the public Python SDK surface.
Top-level implementation packages such as `adapters`, `core`, and `pipeline`
remain private runtime modules even while they are packaged for console scripts.
