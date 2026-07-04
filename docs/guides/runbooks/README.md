# CRK Runbooks

Operational runbooks assume commands are run from the `tc-c-kit` repository
root:

```text
<project_root>/
```

Use these when moving from README examples to repeatable operator workflows.

| Runbook | Use it for |
| --- | --- |
| [Setup Requirements](setup/requirements.md) | Hardware tiers, OS support, pinned tools, optional services, Docker resources, storage, and network requirements. |
| [Initial App Install](setup/install.md) | Local install, optional extras, first case setup, and install smoke checks. |
| [Case Workflow](cases/case-workflow.md) | Source-backed case creation, extraction review, agent prompts, and case-level validation. |
| [Self-Hosted Deployment](setup/self-hosted-deployment.md) | Docker stack first run, daily operation, logs, smoke checks, and shutdown. |
| [Public Output Readiness](cases/public-output-readiness.md) | Validation, contradiction/source-independence/privacy gates, and public-export blockers. |
| [Export Artifacts](outputs/export-artifacts.md) | Manim, evidence board, timeline, case visuals, audit CSVs, and UFB bundle exports. |
