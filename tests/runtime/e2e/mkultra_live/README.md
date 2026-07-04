# MKULTRA Live E2E

Opt-in live workflow coverage for the MKULTRA course sample. These tests hit
public URLs and local services, so they skip unless `CRK_LIVE_MKULTRA=1`.

Expected live services:

- SearXNG through `CRK_SEARXNG_URL`
- Qdrant through `CRK_QDRANT_URL`
- Ollama through `OLLAMA_HOST` and `CRK_MODEL=ollama:<model>`
- Codex through `CRK_LIVE_CODEX=1` and `CRK_CODEX_BIN` when that lane is wanted

Focused targets:

- `moon run crk:test-mkultra-surfaces` checks one temp case through CLI,
  MCP stdio, and a Codex skill-style agent call.
- `moon run crk:test-mkultra-live` runs the full live suite, including
  retrieval, model, OCR, parser, MCP, CLI, and Codex lanes.

The tests use a temporary case workspace and never write to
`data/cases/mkultra_course`.
