# Lesson 3: Skill, MCP, And CLI Workflows

This lesson operates the same `mkultra_course` workspace through three
surfaces: the repo-local skill, the MCP server, and the CLI. The source ledger
under `records/*.jsonl` remains the source of truth in every mode.

## Use CRK As A Skill

Use this prompt with Codex or another skill-aware agent from the repository
root:

```text
Use the truecrime-cult-research skill.
Open data/cases/mkultra_course. Work only from registered sources.
Build extraction packets for the MKULTRA authorization, unwitting testing,
record destruction, MKSEARCH/OFTEN/CHICKWIT, institutional research, Frank
Olson, and controversy-boundary subcases.
Do not infer guilt, membership, motive, or hidden control from proximity.
Treat House witness testimony as testimony unless a primary record supports it.
Keep Finders and Jonestown as boundary records unless exact source spans
support a narrower claim.
```

Route specialized packets explicitly:

```text
Route source preservation through source-capture-preservation.
Route hearing pages and testimony through media-transcript-intelligence.
Route contradiction checks through claim-contradiction-audit.
Route final script/report readiness through narrative-readiness-review,
privacy-redaction-audit, and source-independence-audit.
```

Expected agent outputs:

- New staged packets under `data/cases/mkultra_course/staging/extractions/`.
- No canonical import without human approval.
- Claims separated into `corroborated`, `single_source`, `disputed`,
  `unverified`, and `excluded_from_public_script`.
- A contradiction/missing-evidence note for each controversy lane.

## Test All Three Surfaces

The live surface-acceptance test runs the same temporary MKULTRA case through
CLI commands, MCP stdio calls, and a Codex skill-style agent prompt:

```bash
export CRK_LIVE_MKULTRA=1
export CRK_LIVE_CODEX=1
export CRK_CODEX_BIN=codex

moon run crk:test-mkultra-surfaces
```

The test writes a temp-case `surface_acceptance_transcript.json` with three
sections:

| Section | What It Proves |
| --- | --- |
| `cli` | `crk-ledger` validation/readiness and a dry-run `cr-kit plan` can operate the case. |
| `mcp` | `case_info`, `get_source_text`, `draft_extraction`, `save_extraction_packet`, prompts, and reference resources work over stdio. |
| `agent_skill` | Codex can receive the `truecrime-cult-research` skill-style prompt and return candidate-only review JSON. |

The MCP leg deliberately calls `import_extraction` without `confirm=true` and
expects refusal. The agent leg must report `candidate_only=true` and
`evidence_claim=false`.

## Use CRK Through MCP

Run the MCP server through the `mcp` optional extra:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[mcp]' -- crk-mcp --help
```

Register the stdio server with Claude Code:

```bash
claude mcp add crk -- uv run --directory "$PWD" --cache-dir .uv-cache \
  --no-project --with-editable '.[mcp]' -- crk-mcp
```

Other MCP hosts should use command `uv` with args `run --directory <repo>
--cache-dir .uv-cache --no-project --with-editable '.[mcp]' -- crk-mcp` and
stdio transport. Useful MCP operations for this case:

| Workflow Need | MCP Tool |
| --- | --- |
| Inspect the course case | `case_info`, `get_records`, `get_source_text`. |
| Register or capture sources | `add_source`, `ingest_url`. |
| Parse or OCR sources | `parse_source`, `ocr_source`. |
| Draft and save packets | `draft_extraction`, `save_extraction_packet`. |
| Import after review | `import_extraction` with `confirm=true`. |
| Public outputs | `run_report`, `export_manim`, `export_case_visuals`. |

Example MCP-host prompt:

```text
Use MCP tool get_source_text for case mkultra_course and source
S_SENATE_MKULTRA_1977. Draft a media-transcript packet for the record
destruction and MKSEARCH/OFTEN/CHICKWIT sections. Save it as a staged packet
only; do not import canonical records.
```

## Use CRK Through The CLI

The `crk-ledger` command is best for source-ledger operations:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger validate \
  data/cases/mkultra_course
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger draft-extraction \
  data/cases/mkultra_course S_SENATE_MKULTRA_1977
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger audit-contradictions \
  data/cases/mkultra_course
```

The `cr-kit` command runs the case-builder workflow through `uv`:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  cr-kit plan data/cases/mkultra_course \
  --title "MKUltra Source-Traceable Course Case" \
  --subject "Source-backed MKULTRA course with official, archive, testimony, and boundary records"
```

Execute only after reviewing the planned writes:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  cr-kit plan data/cases/mkultra_course \
  --title "MKUltra Source-Traceable Course Case" \
  --subject "Draft extraction packets for core official MKULTRA sources" \
  --execute
```

If LangGraph checkpoints are installed:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[agentic]' -- \
  cr-kit plan data/cases/mkultra_course \
  --runner langgraph \
  --checkpoint \
  --title "MKUltra Source-Traceable Course Case" \
  --subject "Pause for human review before importing staged packets" \
  --execute
```

Resume after packet review:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  cr-kit resume data/cases/mkultra_course \
  --thread <thread_id> \
  --approve-packet <packet_name>.json \
  --execute
```

## Target Extraction Backlog

| Packet | Source IDs | Review Requirement |
| --- | --- | --- |
| Authorization and control | `S_CIA_MKULTRA_IG_1963`, `S_SENATE_MKULTRA_1977` | Match DCI authorization and MKDELTA/MKULTRA boundaries. |
| Records destruction | `S_SENATE_MKULTRA_1977`, `S_NSARCHIVE_MKULTRA_CONTEXT_2024` | Separate official record from archive commentary. |
| Unwitting testing | `S_CIA_MKULTRA_IG_1963`, `S_ROCKEFELLER_COMMISSION_1975` | Avoid unsupported medical detail; cite exact spans. |
| MKSEARCH/OFTEN/CHICKWIT | `S_SENATE_MKULTRA_1977`, `S_DOD_MKSEARCH_1977_METADATA` | Do not rely on metadata-only DoD record for facts. |
| Institutions and cutouts | `S_SENATE_MKULTRA_1977`, `S_NSARCHIVE_MKULTRA_CONTEXT_2024` | Keep institution ties source-stated and non-accusatory. |
| Boundary cases | Finders, Jonestown, O'Neill testimony, Gateway, STAR GATE | Mark as boundary, disputed, OCR-pending, or metadata-only. |
