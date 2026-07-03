---
name: spec-kanban-agent-orchestration
description: "Coordinate multi-agent implementation from shared spec, plan, and kanban docs. Use when Codex should spawn reviewer, worker, or explorer agents; assign task ownership; keep kanban status current; integrate subagent work; or enforce spec-driven PR and git hygiene."
---

# Spec Kanban Agent Orchestration

Use this skill to coordinate parallel agent work from a shared specification,
implementation plan, and kanban board. The main agent remains the orchestrator:
it owns the critical path, delegates bounded sidecar work, integrates results,
and verifies the final state.

## Required Inputs

Use the paths supplied by the user when available. Otherwise look for the active
set under:

```text
docs/superpowers/specs/
docs/superpowers/plans/
docs/superpowers/kanban/
```

Read the relevant spec, plan, and kanban before spawning agents. If more than
one active set matches, ask the user to pick one or choose the newest matching
topic only when the intent is unambiguous.

## Preflight

1. Run `git status --short --branch`.
2. Read the spec, plan, and kanban.
3. Identify hard dependencies, independent task slices, and owned files.
4. Decide what the main agent should do locally now. Do not delegate the
   immediate blocking task.
5. Spawn subagents only when the user explicitly asks for delegation,
   subagents, workers, reviewers, or parallel agent work.

## Delegation Rules

- Give every worker a task ID list and a disjoint file/module ownership scope.
- Tell workers they are not alone in the codebase and must not revert or
  overwrite other agents' work.
- Prefer workers for bounded implementation slices.
- Prefer explorers for read-only codebase questions.
- Use a reviewer as a read-only role unless the user explicitly wants review
  notes written to disk.
- Avoid multiple agents editing the same file.
- Keep the main agent focused on integration, conflict resolution, and final
  verification.

## Kanban Discipline

Use the current kanban format when one exists. When creating or repairing a
kanban, follow `references/kanban-contract.md`.

Status changes:

- Move a task to `claimed` only when a worker or the main agent owns it.
- Move a task to `in_progress` when edits or analysis begin.
- Move a task to `review` when the owner reports done and tests/checks are
  available.
- Move a task to `done` only after integration and verification.
- Move a task to `blocked` only with a concrete blocker and required unblocker.

## Prompt Templates

Use `references/prompt-templates.md` for worker, reviewer, and explorer prompt
templates. Include the actual spec, plan, kanban paths, owned task IDs, file
ownership, expected output, and test expectations in every delegated prompt.

## Integration Workflow

1. While agents run, do non-overlapping local work.
2. Wait only when the next local step needs a subagent result.
3. Review returned changes or findings before accepting them.
4. Resolve conflicts locally; do not ask workers to fight over shared files.
5. Run the relevant checks from the plan or repository instructions.
6. Update the kanban with completed task IDs, blockers, and review notes.
7. Keep staging path-scoped and do not sweep unrelated dirty files.

## Final Response Shape

Report:

- Spec, plan, and kanban used.
- Agents spawned and task IDs assigned.
- Files changed or reviewed.
- Tests/checks run and results.
- Tasks completed, remaining, or blocked.
- Any reviewer findings or residual risks.
