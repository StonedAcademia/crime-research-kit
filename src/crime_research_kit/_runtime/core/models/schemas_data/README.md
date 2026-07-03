# Packaged record schemas

Read-only mirror of `docs/schemas/` shipped as package data so installed
packages can validate ledger records without a repo checkout. `docs/schemas/`
is canonical; `tests/quality/governance/platform/test_packaging_policy.py::
test_packaged_schema_data_matches_canonical_docs_schemas` keeps this copy in
sync. Edit the canonical files and re-copy; never edit these directly.
