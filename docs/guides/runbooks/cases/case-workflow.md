# Case Workflow Runbook

This runbook shows how to ask Codex or another agent to use the TRCR skills and
agent flows without turning lead discovery into unsourced claims. The full
workflow is split into small reference files.

Commands assume they are run from the `tc-c-kit` repository root so the skill
script path is `.agents/skills/truecrime-cult-research/scripts/tcr.py` and case
work stays under `data/cases/`.

## Workflow Shards

| Step | File |
|---|---|
| Case workspace, source registration, and extraction packets | [Setup and extraction](case-workflow/setup-extraction.md) |
| Conservative name linking and resumable agent flow | [Agent flow](case-workflow/agent-flow.md) |
| Review prompts, validation, exports, and done criteria | [Review and export](case-workflow/review-export.md) |

## Working Rule

Every public-facing point must reduce to:

```text
claim -> source_ids -> reliability grade -> confidence/status -> privacy review -> export
```

If that chain is incomplete, keep the point out of public scripts, evidence
boards, Manim exports, and public bundles except as explicitly unknown,
lead-only, or disputed.
