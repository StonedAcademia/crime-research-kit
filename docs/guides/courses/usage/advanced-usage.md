# Advanced Usage

This guide covers high-control workflows: agentic runs, checkpoints, retrieval,
exports, and hard-case review patterns.

## Plan Before Executing

Use `cr-kit plan` to inspect the workflow before allowing writes:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  cr-kit plan data/cases/mkultra_course \
  --title "MKUltra Source-Traceable Course Case" \
  --subject "Source-backed MKULTRA course with official, archive, testimony, and boundary records"
```

Execute only after reviewing the plan:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  cr-kit plan data/cases/mkultra_course \
  --title "MKUltra Source-Traceable Course Case" \
  --subject "Draft extraction packets for core official MKULTRA sources" \
  --execute
```

## Use Checkpoints For Long Runs

When the `agentic` extra is installed, use checkpoints for workflows that need
human review between steps:

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

## Add Retrieval And Memory Deliberately

Local retrieval and memory can help prioritize source review, but they do not
raise claim confidence by themselves. Use them to find candidate spans, then
promote only the claims backed by registered source locators.

Recommended boundary:

```text
retrieval result -> source text -> extraction packet -> human review -> import
```

## Export Only After Gates Pass

Before visual exports, evidence boards, scripts, or reports:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger audit-public-export data/cases/mkultra_course
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger review-narrative-readiness data/cases/mkultra_course --require-spans
```

Then generate outputs:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger report data/cases/mkultra_course
uv run --cache-dir .uv-cache --no-project --with-editable . -- \
  crk-ledger export-case-visuals data/cases/mkultra_course
```

## Hard-Case Review Pattern

For controversial or boundary-heavy subjects:

1. Split each public point into a single claim.
2. Attach source IDs and locators.
3. Identify whether the source is official record, testimony, archive context,
   interpretation, or metadata-only lead.
4. Search for contradictions, corrections, and missing records.
5. Mark unresolved claims as disputed, unverified, or excluded from public
   output.

## Done When

- Agentic runs pause before canonical imports.
- Retrieval/memory output is treated as discovery, not evidence.
- Public exports pass audit and narrative-readiness gates.
