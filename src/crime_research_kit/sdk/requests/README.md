# SDK Request Models

`crime_research_kit.sdk.requests` contains the strict pydantic request models
used by public SDK operations.

The `OperationSpec.request_model` value in `crime_research_kit.sdk.operations`
is a model name, not a runtime module path. Resolve that name through
`REQUEST_MODELS` or `get_request_model()` before validating catalog-driven
payloads or generating adapter schemas.

Use these models when integration code needs a stable payload contract before
calling a client method. `validate_request()` accepts an operation name,
`OperationSpec`, or model name, rejects unexpected fields, and returns the
typed request object.

Workflow request models remain part of this public surface:

- `WorkflowPlanRequest`
- `WorkflowResumeRequest`

The request package documents operation inputs only. It does not make runtime
implementation modules public SDK imports.
