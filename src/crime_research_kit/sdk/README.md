# SDK

`crime_research_kit.sdk` is the stable Python SDK namespace.

Current surface:

- `CrkContext` carries caller-provided roots, privacy defaults, resolved
  settings, metadata, and transport mode.
- `CrkClient` is the top-level SDK entrypoint.
- `CaseClient` is a case-scoped handle that stores the resolved case context.
- `CasesClient` and `CaseRecordsClient` expose case listing, case info, public
  record reads, and source-text reads.
- `CaseSourcesClient` exposes source registration, URL ingestion,
  preservation, discovery, parsing, and OCR wrappers.
- `CaseExtractionsClient` exposes staged extraction draft, list, read, save,
  reviewed import, and lead-only NER suggestion wrappers.
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
