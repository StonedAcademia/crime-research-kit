# SDK

`crime_research_kit.sdk` is the stable Python SDK namespace.

Current surface:

- `CrkContext` carries caller-provided paths and execution metadata.
- `OperationResult` and `OperationWarning` define the stable SDK result
  envelope.
- `CrkError` and related subclasses define stable SDK error codes.
- `SafetyTier` and `OperationSpec` describe public operation wrappers before
  they are wired.
- `list_operations()` returns the current public operation specification
  catalog.

The operation catalog is intentionally empty until operation wrappers are
promoted into the SDK.
