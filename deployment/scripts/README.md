# Deployment Scripts

Scripts are grouped by operational intent:

- `bootstrap.sh` / `bootstrap.ps1` install the minimum toolchain (proto plus
  pinned moon/python/uv) before first use. Pass `--configure` / `-Configure`
  to write ignored local deployment env files through `bootstrap_env.py`.
- `bootstrap_env.py` renders workflow-specific `.env` files with restricted
  permissions and can generate ignored local SearXNG settings when exposure is
  explicitly requested.
- `bootstrap/` contains the stdlib-only implementation behind
  `bootstrap_env.py`.
- `checks/` runs local validation, smoke checks, and branch gates.
- `local/` operates the self-hosted Docker Compose stack.
- `tools/` handles governance tool fetches, install compatibility helpers, and
  export helpers.

When adding a script, choose the group by how an operator uses it. If a group
would exceed the repository governance limit, split by a clearer workflow name
instead of using miscellaneous buckets.
