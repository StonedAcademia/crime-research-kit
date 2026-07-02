# Move Lane Registry Under `docs/registry/`

**Status:** Implemented
**Date:** 2026-07-02
**Goal:** Move the canonical lane/template registry from `docs/lanes.json` to
`docs/registry/lanes.json` without creating a second source of truth or
breaking the CLI, case-builder loader, MCP docs, generated skill references, or
governance tests.

## Target Layout

```text
docs/
  registry/
    lanes.json
  schemas/
    lanes.schema.json
```

`docs/registry/lanes.json` becomes the only canonical lane/template registry.
Do not leave a duplicate `docs/lanes.json` copy behind. If compatibility is
needed, add an explicit error message that points callers to the new path rather
than silently loading stale data.

## Pre-Refactor Consumers

| Surface | Current dependency |
| --- | --- |
| `src/case_builder/lanes/registry.py` | `default_lanes_path()` returns `docs/lanes.json`. |
| `src/case_builder/lanes/docs.py` | Generated-doc marker and `generated_paths()` read `docs/lanes.json`. |
| `.agents/skills/truecrime-cult-research/scripts/tcr.py` | `lane_registry_path()` searches for `docs/lanes.json` from script and cwd roots. |
| `tests/governance/test_lanes_json.py` | Loads `ROOT / "docs" / "lanes.json"`. |
| `tests/unit/test_lanes_registry.py` | Asserts the default path is `docs/lanes.json`. |
| `tests/governance/test_skill_docs_tool_access.py` | Requires skill docs to mention `docs/lanes.json`. |
| Generated references | Markers say `Generated from docs/lanes.json`. |
| Skill docs | Each lane skill says lane/template metadata comes from `docs/lanes.json`. |
| Public docs | README, MCP docs, and API spec point to `docs/lanes.json`. |

## Implementation Tasks

### Task 1: Move the registry file

- Create `docs/registry/`.
- Move `docs/lanes.json` to `docs/registry/lanes.json` with `git mv`.
- Keep `docs/registry/lanes.schema.json` beside the registry data so registry
  shape validation stays in the same docs namespace.

Validation:

```bash
test -f docs/registry/lanes.json
test ! -f docs/lanes.json
python -m json.tool docs/registry/lanes.json >/tmp/trcr-lanes.json
```

### Task 2: Update runtime loaders

- Update `src/case_builder/lanes/registry.py` so `default_lanes_path()` returns
  `docs/registry/lanes.json`.
- Update `.agents/skills/truecrime-cult-research/scripts/tcr.py` so
  `lane_registry_path()` searches:
  - `<repo>/docs/registry/lanes.json`
  - `<cwd>/docs/registry/lanes.json`
  - `<cwd>/tc-c-kit/docs/registry/lanes.json`
- Update the missing-registry error text to name `docs/registry/lanes.json`.

Validation:

```bash
python -m pytest tests/unit/test_lanes_registry.py tests/governance/test_lanes_json.py -q
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction --help
```

### Task 3: Update generated-doc code and outputs

- Update `src/case_builder/lanes/docs.py` markers from
  `docs/lanes.json` to `docs/registry/lanes.json`.
- Regenerate:
  - `.agents/skills/truecrime-cult-research/references/lane_registry.md`
  - `.agents/skills/public-records-router/references/routing_matrix.md`

Validation:

```bash
PYTHONPATH=src python -m case_builder.lanes.docs --write
PYTHONPATH=src python -m case_builder.lanes.docs --check
python -m pytest tests/governance/test_lanes_docs_generation.py -q
```

### Task 4: Update skill and public docs

- Replace active references to `docs/lanes.json` with
  `docs/registry/lanes.json` in:
  - `README.md`
  - `docs/integrations/mcp-server.md`
  - `docs/reference/skill-api-spec.md`
  - `src/case_builder/README.md`
  - `src/case_builder/lanes/README.md`
  - `.agents/skills/*/SKILL.md`
- Historical files under `docs/superpowers/` can keep old paths when they are
  describing the state at the time, but new plans/specs should use the new
  registry path.

Validation:

```bash
rg -n "docs/lanes\\.json" README.md docs src .agents tests
python -m pytest tests/governance/test_skill_docs_tool_access.py -q
```

Expected: only historical `docs/superpowers/` references remain, unless those
are intentionally updated.

### Task 5: Run the normal gates

```bash
moon run trcr:check
moon run trcr:test-governance
moon run trcr:test-unit
git diff --check
```

If Moon task names change, use the equivalent pytest commands for governance
and unit suites.

## Commit Boundary

Use one commit for the full registry move because loader, docs, generated
references, and governance tests must stay in sync:

```bash
git add docs/registry/lanes.json docs/registry/lanes.schema.json \
  src/case_builder/lanes .agents/skills tests README.md docs/integrations \
  docs/reference
git add -u docs/lanes.json
git commit -m "docs: move lane registry under docs registry"
```
