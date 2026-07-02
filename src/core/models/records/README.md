# Record models

Pydantic `BaseModel` classes mirroring `docs/schemas/` — the typed in-memory
representation for ledger rows. The JSON Schemas stay canonical for on-disk
validation; `tests/quality/governance/policy/test_schemas.py`
keeps required fields, property names, and enums aligned. `extra="allow"` and
`model_dump(exclude_none=True)` preserve round-trip fidelity for rows carrying
fields the schemas allow via `additionalProperties`.
