# E2E & Smoke Tests for the Local-Stack Subsystems

**Date:** 2026-07-03
**Status:** Approved design (pending spec review)
**Scope:** Document parsing (Docling), OCR (OCRmyPDF), retrieval + Qdrant (LlamaIndex),
SearXNG discovery, and the self-hosted container stack.

## Problem

The `e2e` and `smoke` pytest lanes today are entirely in-process and dry-run: they never
exercise a real optional dependency or a live service. The only validation of the real
self-hosted stack is a bash script (`deployment/scripts/checks/smoke/smoke-test.sh`, run via
`moon run crk:docker-smoke` *inside the container*), which curls Qdrant `/readyz`, SearXNG
`/search`, and Ollama `/api/tags`, and checks the `tesseract`/`gs`/`ocrmypdf` binaries.

That leaves a gap: no pytest-level E2E or smoke coverage exercises OCR, Docling parsing,
retrieval, or Qdrant against either real dependencies or realistic fakes. The document
layer (`build_evidence_documents`) is unit-tested offline, but the `parse_source`,
`ocr_source`, `index_case`, `query_case`, and `discover_sources` operations are only
tested at the level of CLI argument parsing and graceful-degradation error messages.

## Goals

- Cover each subsystem end-to-end through its public operation, not just its helpers.
- Keep the **default CI lane green** whether or not optional extras or the stack are present.
- Provide **live tests that genuinely pass** against a real stack, sharing a test body with
  their hermetic counterparts so the two cannot drift.
- Add the minimal production seam needed to make retrieval testable hermetically, without
  changing production behavior.

## Non-goals

- Rewriting the bash `docker-smoke` gate (it stays as the in-container liveness check; the
  new pytest `e2e` liveness test is a sibling, not a replacement).
- Testing model quality / retrieval relevance. We assert the code path and data contracts
  (privacy filter, metadata, scores present), not embedding accuracy.
- Adding any required dependency. Everything new stays behind existing optional extras.

## Posture: layered, three tiers

All three tiers coexist; the default lane stays green regardless of environment.

| Tier | Lane | Deps needed | Skip rule |
|---|---|---|---|
| **Contract / degradation** | `smoke` | none | never skips — asserts each op raises the clean "install the extra" `RuntimeError` when its dep is absent, and that CLI commands parse |
| **Hermetic component** | `smoke` / `integration` | optional extra installed, no network | `importorskip` on docling / ocrmypdf / llama-index; skip if a required binary is missing |
| **Live end-to-end** | `e2e` | extra + live docker stack | skip unless `CRK_QDRANT_URL` / `CRK_SEARXNG_URL` / `OLLAMA_HOST` are reachable |

## Production change: retrieval injection seam (option 3a)

`_build_index` in `adapters/io/retrieval/index.py` currently hardcodes
`QdrantClient(url=qdrant_url)` and `HuggingFaceEmbedding(model_name=embed_model)`, so there
is no way to run it without a live Qdrant and a downloaded HF model. We add an injection
seam that leaves production behavior unchanged:

- `_build_index` (and, threaded through, `index_case` / `query_case`) accept optional
  `client` (a Qdrant client) and `embed` (an embedding model object) parameters.
- When omitted, the defaults construct `QdrantClient(url=...)` + `HuggingFaceEmbedding(...)`
  exactly as today — **no behavior change for the CLI, ops core, or MCP callers.**
- The seam is internal/keyword-only and does not alter any public CLI or ops signature; it
  exists so tests can inject a fake. Keep `index.py` under the 200-LOC governance limit —
  if the seam pushes it over, split the client/embedder construction into a small
  `_backends.py` helper module (with its own `README.md`).

The hermetic tests inject `QdrantClient(location=":memory:")` plus a deterministic
`MockEmbedding` (from `llama_index.core.embeddings.mock_embed_model`; if that import path is
unavailable in the pinned version, a minimal `BaseEmbedding` subclass returning fixed-length
deterministic vectors). The live tests inject nothing (or an explicit real client) and run
the real embedder.

## Test design per subsystem

### 1. Document parsing (Docling)

- **Fixture:** add a tiny real-text PDF at `tests/fixtures/docs/sample_report.pdf` (a few
  lines of known text). Committed, small.
- **Hermetic** (`importorskip("docling")`): copy the synthetic case, register the fixture as
  a source with a local `raw_path`, run `parse_source`. Assert extracted text contains the
  known strings, `text_path` is written under the case, the source record is updated, and a
  rerun without `force` returns `skipped: True`.
- **Contract:** with docling absent, `parse_source` raises `RuntimeError` mentioning the
  documents extra.

### 2. OCR (OCRmyPDF)

- Reuses the same fixture PDF.
- **Hermetic** (`importorskip`/binary guard on `ocrmypdf`, `tesseract`, `gs`): run
  `ocr_source`. Assert the sidecar text file and output PDF are written under
  `raw/sources` / `raw/ocr`, and a rerun without `force` returns `skipped: True`. Because the
  fixture already has a text layer, this exercises the `--skip-text` path.
- **Contract:** binary-missing path surfaces a clean error (subprocess failure is reported,
  not swallowed).

### 3. Retrieval + Qdrant

- **Hermetic** (`importorskip` on llama-index + qdrant-client): inject
  `QdrantClient(location=":memory:")` + `MockEmbedding`. Run `index_case` then `query_case`
  on the synthetic case. Assert `document_count > 0`, the collection name is derived from the
  case id, results carry `score`/`text`/`metadata`, and a `public_export: false` record is
  excluded from public results but present with `include_private=True`.
- **Live** (`e2e`, skip unless `CRK_QDRANT_URL` reachable): the **same parametrized test
  body** against real Qdrant with the real embedder. This is the "equivalent test that passes
  for the live instance." Parametrization (`backend="memory"` vs `backend="live"`) keeps the
  assertions identical so the paths cannot drift.
- **Contract:** with the retrieval extra absent, `index_case` raises `RuntimeError` mentioning
  the retrieval extra.

### 4. SearXNG discovery

- **Hermetic:** call `discover_sources` with a monkeypatched httpx transport returning canned
  SearXNG JSON. Assert a lead-only candidate report is written, candidates carry title/url,
  and the safety framing is preserved (leads only — no claims/entities created, nothing marked
  as evidence or `public_export: true` by this step).
- **Live** (`e2e`, skip unless `CRK_SEARXNG_URL` reachable): same assertions against real
  SearXNG. Shares the report-shape assertions with the hermetic test.

### 5. Self-hosted stack liveness

- **Live** (`e2e`, skip unless reachable): a pytest sibling to the bash smoke test that
  reaches Qdrant `/readyz`, SearXNG `/search?...&format=json`, and Ollama `/api/tags`. Skips
  cleanly when the stack is down. The bash `docker-smoke` script remains the in-container gate.

## File / directory layout

Respecting the repository-shape rule (1–4 direct files, 0–3 direct child dirs per governed
directory; every Python-bearing dir has a `README.md`):

```
tests/quality/smoke/local_stack/
  README.md
  conftest.py            # shared skip-guards + fixtures (see below)
  test_parsing.py        # docling hermetic + contract
  test_ocr.py            # ocrmypdf hermetic + contract
  test_discovery.py      # searxng hermetic + contract

tests/runtime/e2e/local_stack/
  README.md
  conftest.py            # live-service reachability guards
  test_retrieval.py      # parametrized memory + live (Qdrant)
  test_stack_liveness.py # Qdrant/SearXNG/Ollama liveness

tests/fixtures/docs/
  README.md
  sample_report.pdf
```

If `test_retrieval.py` needs both hermetic and live in one file, the memory case can also
live in `smoke/local_stack/` — final placement chosen at implementation time to satisfy the
4-file cap; the parametrized body stays single-sourced (shared helper) regardless.

### Shared skip-guards (`conftest.py` helpers)

- `requires_binary(name)` — skip if `shutil.which(name)` is None.
- `requires_extra(module)` — thin wrapper over `pytest.importorskip`.
- `live_service(env_var, health_path)` — skip unless the URL from the env var answers a fast
  health probe (short timeout, connection error → skip, not fail).
- Reuse the existing `synthetic_case_copy` fixture from the top-level `tests/conftest.py`.

## Runner integration

The new tests are auto-markered by the existing `pytest_collection_modifyitems` hook
(directory name → marker), so `moon run crk:test-smoke` and `moon run crk:test-e2e` pick them
up with no task changes. The live tier self-skips in default runs. No new moon task is
required; `docker-smoke` is unchanged.

## Verification approach (implementation-time, adjustable)

Live tests are skip-gated for CI but must be proven to pass against a real stack. Default
plan: bring up **Qdrant + SearXNG** (small, fast images) via the compose tooling and confirm
the retrieval + discovery + liveness live tests pass; attempt the full stack including Ollama
if feasible in-session, otherwise hand the Ollama-dependent liveness check to the operator.
This choice affects only how far verification goes in-session, not the tests themselves.

## Risks / open items

- **MockEmbedding import path** may differ across the pinned `llama-index-core` version;
  fallback is a minimal deterministic `BaseEmbedding` subclass.
- **`index.py` 200-LOC ceiling** — the seam may force splitting backend construction into a
  helper module; budget for that.
- **Fixture PDF** must be genuinely small and license-clean (synthetic text we author).
- **Live Ollama verification** depends on a large model pull; may be deferred to the operator
  per the verification-approach note above.
