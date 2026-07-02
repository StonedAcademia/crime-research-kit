# TRCR Runbooks

Operational runbooks assume commands are run from the `tc-c-kit` repository
root:

```text
<projects-root>/true-crime-research/tc-c-kit
```

Use these when moving from README examples to repeatable operator workflows.

| Runbook | Use it for |
| --- | --- |
| [Initial App Install](install.md) | Local install, optional extras, first case setup, and install smoke checks. |
| [Case Workflow](case-workflow.md) | Source-backed case creation, extraction review, agent prompts, and case-level validation. |
| [Self-Hosted Deployment](self-hosted-deployment.md) | Docker stack first run, daily operation, logs, smoke checks, and shutdown. |
| [Public Output Readiness](public-output-readiness.md) | Validation, contradiction/source-independence/privacy gates, and public-export blockers. |
| [Export Artifacts](export-artifacts.md) | Manim, evidence board, timeline, charts, clusters, analysis charts, and UFB v2 bundle exports. |
