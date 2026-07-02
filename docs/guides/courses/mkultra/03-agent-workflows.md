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

## Use CRK Through MCP

Install the MCP extra if it was not installed with the dev environment:

```bash
source .venv/bin/activate
python -m pip install -e '.[mcp]'
```

Register the stdio server with Claude Code:

```bash
claude mcp add crk -- "$PWD/.venv/bin/crk-mcp"
```

Other MCP hosts should use command `$PWD/.venv/bin/crk-mcp` with stdio
transport. Useful MCP operations for this case:

| Workflow Need | MCP Tool |
| --- | --- |
| Inspect the course case | `case_info`, `get_records`, `get_source_text`. |
| Register or capture sources | `add_source`, `ingest_url`. |
| Parse or OCR sources | `parse_source`, `ocr_source`. |
| Draft and save packets | `draft_extraction`, `save_extraction_packet`. |
| Import after review | `import_extraction` with `confirm=true`. |
| Public outputs | `run_report`, `export_manim`, `export_case_charts`. |

Example MCP-host prompt:

```text
Use MCP tool get_source_text for case mkultra_course and source
S_SENATE_MKULTRA_1977. Draft a media-transcript packet for the record
destruction and MKSEARCH/OFTEN/CHICKWIT sections. Save it as a staged packet
only; do not import canonical records.
```

## Use CRK Through The CLI

The plain script path is best for source-ledger operations:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate \
  data/cases/mkultra_course
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction \
  data/cases/mkultra_course S_SENATE_MKULTRA_1977
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-contradictions \
  data/cases/mkultra_course
```

The installed `cr-kit` command runs the case-builder workflow:

```bash
.venv/bin/cr-kit plan data/cases/mkultra_course \
  --title "MKUltra Source-Traceable Course Case" \
  --subject "Source-backed MKULTRA course with official, archive, testimony, and boundary records"
```

Execute only after reviewing the planned writes:

```bash
.venv/bin/cr-kit plan data/cases/mkultra_course \
  --title "MKUltra Source-Traceable Course Case" \
  --subject "Draft extraction packets for core official MKULTRA sources" \
  --execute
```

If LangGraph checkpoints are installed:

```bash
.venv/bin/cr-kit plan data/cases/mkultra_course \
  --runner langgraph \
  --checkpoint \
  --title "MKUltra Source-Traceable Course Case" \
  --subject "Pause for human review before importing staged packets" \
  --execute
```

Resume after packet review:

```bash
.venv/bin/cr-kit resume data/cases/mkultra_course \
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
