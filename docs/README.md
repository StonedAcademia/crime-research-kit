# Documentation Map

This directory keeps durable project documentation in small, named groups:

- `guides/` contains human-facing architecture notes, integration guides, runbooks, and the skill API contract.
- `registry/` contains canonical machine-facing registries such as lane metadata.
- `schemas/` contains JSON Schemas grouped by the record domain they validate.

Keep new documentation close to the workflow or contract it serves. If a guide
starts collecting unrelated procedures, split it into a named runbook group.

## Document Structure

| Path | Purpose |
| --- | --- |
| `README.md` | Project orientation, safety boundary, capability summary, and links. |
| `docs/README.md` | Documentation map and grouping rules. |
| `docs/guides/architecture/` | System architecture, ownership boundaries, and orchestration design. |
| `docs/guides/integrations/` | Host, protocol, and external-tool integration guides. |
| `docs/guides/skill-api-spec.md` | Stable machine-facing contracts and API/reference material. |
| `docs/guides/runbooks/` | Operator procedures and repeatable workflows. Long command sequences belong here. |
| `docs/guides/runbooks/setup/requirements.md` | Hardware, OS, toolchain, optional-service, Docker, storage, and network requirements. |
| `docs/schemas/` | JSON Schemas grouped by case, evidence, and review records. |
| `docs/registry/` | Canonical lane and extraction-template vocabulary. |
| `docs/superpowers/` | Planning/spec history for larger implementation phases. |
| `.agents/skills/` | Repo-local skills and reusable workflow instructions. |
| `src/` | Case-builder app modules, LangGraph runner, MCP surface, retrieval, memory, and ops wrappers. |
| `deployment/` | Self-hosted stack, deployment scripts, and local-service configuration. |
| `data/examples/` | Tracked synthetic fixtures. Generated case work belongs in ignored `data/cases/`. |
