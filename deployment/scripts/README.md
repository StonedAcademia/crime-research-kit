# Deployment Scripts

Scripts are grouped by operational intent:

- `bootstrap.sh` / `bootstrap.ps1` install the minimum toolchain (proto plus
  pinned moon/python/uv) before first use.
- `checks/` runs local validation, smoke checks, and branch gates.
- `local/` operates the self-hosted Docker Compose stack.
- `tools/` handles governance tool fetches, install compatibility helpers, and
  export helpers.

When adding a script, choose the group by how an operator uses it. If a group
would exceed the repository governance limit, split by a clearer workflow name
instead of using miscellaneous buckets.
