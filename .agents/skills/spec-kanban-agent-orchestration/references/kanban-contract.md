# Kanban Contract

Use this contract when creating or normalizing a spec/plan/kanban board for
multi-agent work.

## Recommended Paths

```text
docs/superpowers/specs/YYYY-MM-DD-topic.md
docs/superpowers/plans/YYYY-MM-DD-topic.md
docs/superpowers/kanban/topic.md
```

## Task Fields

Each task should provide:

| Field | Meaning |
| --- | --- |
| `id` | Stable task ID such as `T-001`. |
| `title` | Short action-oriented task name. |
| `status` | `todo`, `claimed`, `in_progress`, `review`, `done`, or `blocked`. |
| `owner` | `main`, `reviewer`, or worker label such as `worker-a`. |
| `files` | Expected file/module ownership. |
| `depends_on` | Task IDs that must finish first. |
| `checks` | Focused validation commands or review gates. |
| `notes` | Blockers, assumptions, or reviewer findings. |

## Status Semantics

- `todo`: not owned.
- `claimed`: owner assigned, work not started.
- `in_progress`: active work.
- `review`: implementation done, awaiting reviewer or main-agent integration.
- `done`: integrated and verified.
- `blocked`: cannot proceed without a named dependency, user input, or external
  state change.

## Board Shape

Use Markdown tables for small boards and repeated task cards for larger work.
Preserve the existing format if the repo already has one.

Small-board table:

```markdown
| ID | Status | Owner | Task | Files | Depends On | Checks | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T-001 | todo |  | Add parser tests | `tests/...` |  | `pytest ...` |  |
```

Large-task card:

```markdown
## T-001: Add parser tests

- Status: todo
- Owner:
- Files: `tests/...`
- Depends on:
- Checks: `pytest ...`
- Notes:
```
