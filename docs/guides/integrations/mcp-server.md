# TRCR MCP Server

`trcr-mcp` exposes the case-builder ops core to MCP hosts over stdio.

## Install and Register

```bash
uv pip install -p .venv/bin/python -e '.[mcp]'

# Claude Code:
claude mcp add trcr -- <project_root>/.venv/bin/trcr-mcp
```

For other hosts, use command
`<project_root>/.venv/bin/trcr-mcp`
with stdio transport. If the venv is activated, `trcr-mcp` is equivalent.

Optional environment:

- `TRCR_CASES_ROOT`: defaults to `<repo>/data/cases`.
- `TRCR_SKILL_ROOT`: defaults to the repo-local `.agents` skill copy.
- `TRCR_MODEL`, Qdrant, and SearXNG settings come from the environment as usual.

## Tool Tiers

| Tier | Tools | Writes |
| --- | --- | --- |
| Read/query/report | `case_info`, `list_cases`, `get_records`, `get_source_text`, `query_case`, `list_staged_packets`, `run_report` | No canonical records; `run_report` may write a derived evidence-board export. |
| Staged write | `discover_sources`, `ingest_url`, `add_source`, `parse_source`, `ocr_source`, `draft_extraction`, `save_extraction_packet`, `link_names`, `plan_public_records` | `staging/`, `raw/`, and source registry. |
| Gated | `import_extraction`, `export_manim`, `export_case_charts`, `export_analysis_charts` | Canonical records or exports. `import_extraction` requires `confirm=true` after explicit user approval. Exports are public-safe by default. |

`plan_public_records` accepts public-record lane IDs from `docs/registry/lanes.json`.
`draft_extraction` accepts template IDs from the same registry. Generated human
references live in
`.agents/skills/truecrime-cult-research/references/lane_registry.md` and
`.agents/skills/public-records-router/references/routing_matrix.md`.

## Resources and Prompts

Resources:

- `trcr://cases/{case}/case.json`
- `trcr://cases/{case}/records/{record_type}`: public-safe JSONL
- `trcr://cases/{case}/staging/extractions/{name}`
- `trcr://references/{controlled_vocabularies|topic_extraction_templates}`

Prompts:

- `start_case`
- `process_source`
- `review_packet`
- `public_readiness`

These prompts carry the skill workflow guidance for hosts without repo-local
skills.

## Safety

The safety contract lives in `case_builder.ops`: staged-write classification,
privacy filtering, guilt-label lint, and gated import. The server adds
slug-rooted case resolution and never touches `tcr.py` or ledger files directly.
Records with `public_export: false` never appear in default reads, resources, or
exports.
