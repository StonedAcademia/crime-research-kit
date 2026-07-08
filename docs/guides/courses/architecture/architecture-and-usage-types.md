# Architecture And Usage Types

CRK has several operator surfaces, but they all work against the same local
case workspace and source-ledger contract.

## Mental Model

```text
source capture -> raw/text source files -> staged extraction packets
  -> human review -> records/*.jsonl -> audits -> exports
```

The source ledger is the contract. CLI commands, MCP tools, agent skills, and
local services are different ways to operate that contract.

## Usage Types

| Surface | Best For | Boundary |
| --- | --- | --- |
| CLI | Repeatable source capture, validation, imports, audits, and exports. | Most deterministic surface; use it for scripted or reviewable operations. |
| MCP | Tool use from Claude Code or another MCP host. | Host can inspect and draft packets, but canonical imports still require explicit confirmation. |
| Skills | Research-lane routing and specialized extraction guidance. | Agent output is draft work; source records remain authoritative. |
| `cr-kit` workflow | Planning, agentic packet drafting, checkpoints, and resume flows. | Use `--execute` only after reviewing planned writes. |
| Local services | OCR, retrieval, local LLMs, vector search, and memory. | Discovery aids only; they do not create evidence. |

## CLI Layer

Use `crk-ledger` for ledger operations:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger validate data/cases/mkultra_course
```

Use `cr-kit` for case-builder workflows:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  cr-kit plan data/cases/mkultra_course --title "Course Case" --subject "Draft packets"
```

## MCP Layer

Run the MCP server with the `mcp` extra:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[mcp]' -- crk-mcp
```

Useful MCP operations:

| Need | Tool Family |
| --- | --- |
| Inspect a case | `case_info`, `get_records`, `get_source_text`. |
| Add or capture sources | `add_source`, `ingest_url`. |
| Parse or OCR sources | `parse_source`, `ocr_source`. |
| Draft staged work | `draft_extraction`, `save_extraction_packet`. |
| Import reviewed packets | `import_extraction` with explicit confirmation. |
| Build outputs | `run_report`, `export_case_visuals`. |

## Skill Layer

Skills guide the research method. Use the narrowest relevant lane:

- `source-capture-preservation` for provenance.
- `media-transcript-intelligence` for hearings, interviews, and transcripts.
- `claim-contradiction-audit` for disputed points.
- `privacy-redaction-audit` before public sharing.
- `narrative-readiness-review` before scripts, reports, and video exports.

## Data Layer

Case data is newline-delimited JSON under `records/`. Raw source files and
generated exports stay in ignored case directories. Public examples can point
to source IDs and citation starters, but should not commit raw downloaded
source material unless deliberately promoted as a fixture.

## Choosing A Surface

| If You Need To | Start With |
| --- | --- |
| Reproduce a command exactly | CLI. |
| Let an AI host inspect sources and draft packets | MCP. |
| Ask for lane-specific research judgment | Skills. |
| Run a multi-step workflow with pauses | `cr-kit plan` and checkpoints. |
| Prepare a public report or video | CLI audits, then exports. |

## Done When

- Operators can choose CLI, MCP, skill, or workflow mode intentionally.
- Every mode still routes claims through source IDs, locators, review, and
  public-output gates.
