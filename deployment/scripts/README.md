# Deployment Scripts

Scripts are grouped by operational intent:

- `checks/` runs local validation, smoke checks, and branch gates.
- `local/` operates the self-hosted Docker Compose stack.
- `tools/` handles install, virtualenv command execution, and export helpers.

When adding a script, choose the group by how an operator uses it. If a group
would exceed the repository governance limit, split by a clearer workflow name
instead of using miscellaneous buckets.
