# Local-stack end-to-end tests

Live/near-live tests for the self-hosted subsystems.

- `test_retrieval.py` — Qdrant-backed index/query round-trip, parametrized over an
  in-memory Qdrant (`:memory:`, always runs when the retrieval extra is installed)
  and a live Qdrant (`CRK_QDRANT_URL`, skipped unless reachable). Both use a
  deterministic `MockEmbedding`, so the live case isolates the real Qdrant wire path.
- `test_stack_liveness.py` — Qdrant/SearXNG/Ollama liveness probes (skip unless reachable).

Run the live tier against a stack:

    CRK_QDRANT_URL=http://localhost:6333 \
      uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,retrieval]' \
      -- python -m pytest tests/runtime/e2e/local_stack -v

Do **not** create an `__init__.py` here (see Global Constraints).
