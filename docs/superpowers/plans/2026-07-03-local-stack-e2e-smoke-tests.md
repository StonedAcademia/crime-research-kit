# Local-Stack E2E & Smoke Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add layered E2E and smoke tests that exercise OCR, Docling parsing, retrieval + Qdrant, SearXNG discovery, and self-hosted stack liveness through their public operations, keeping the default CI lane green while providing live tests that genuinely pass against a real stack.

**Architecture:** Three tiers — contract/degradation (no deps), hermetic component (optional extra installed, no network), and live end-to-end (extra + live docker stack, skip-gated). A small internal injection seam in `index.py` lets retrieval run against `QdrantClient(location=":memory:")`; a parametrized test shares one body between the hermetic (`:memory:`) and live (real Qdrant URL) backends so they cannot drift. Both retrieval tiers use a deterministic `MockEmbedding`, so the only variable under test in the live case is the real Qdrant wire path.

**Tech Stack:** pytest, httpx `MockTransport`, LlamaIndex (`llama-index-core`, `qdrant-client`, `MockEmbedding`), Docling, OCRmyPDF, pymupdf (fixture authoring), moon task runner.

## Global Constraints

- Every Python module in `src/` stays under **200 non-comment LOC**; every Python-bearing directory keeps a `README.md` — enforced by `tests/quality/governance/test_repository_shape.py`.
- Each governed directory has **1–4 direct files and 0–3 direct child directories**. Only `data/` and `docs/superpowers/` are skipped.
- **No new required dependencies.** Everything new stays behind the existing optional extras (`documents`, `retrieval`); tests import them lazily and skip when absent.
- Test category markers are applied automatically by directory name via `pytest_collection_modifyitems` in `tests/conftest.py` (dir contains `smoke`/`e2e`/`integration`/`unit`/`governance` → that marker). No manual `@pytest.mark` needed.
- **Do not add `__init__.py`** to any new test directory. Sibling test dirs (`tests/quality/smoke`, `tests/runtime/e2e`) use no package markers, and adding one both breaks that convention and eats a slot against the 4-file directory cap.
- Optional-dependency ops must **degrade gracefully**: absent dep → clean `RuntimeError` naming the extra, not an ImportError traceback.
- Production behavior of `index_case`/`query_case`/`discover_sources` must be **unchanged** for CLI, ops-core, and MCP callers. New parameters are optional and keyword-only.
- Branch hygiene: do this work on a focused `test/*` branch off `dev`; stage only intended paths (the working tree has unrelated in-progress SDK changes — never stage those).
- Single-test invocation form: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest <path>::<test> -v`. For the extras, swap the extra set: `'.[dev,documents]'` or `'.[dev,retrieval]'`.

---

### Task 0: Create the working branch

**Files:** none (git only)

- [ ] **Step 1: Confirm clean intent and branch**

```bash
git status --short --branch
git switch -c test/local-stack-e2e-smoke dev
```

Expected: new branch `test/local-stack-e2e-smoke` created from `dev`. The unrelated `M src/crime_research_kit/sdk/*` files remain unstaged and must stay that way.

---

### Task 1: PDF test fixture

**Files:**
- Create: `tests/fixtures/docs/README.md`
- Create: `tests/fixtures/docs/make_sample_report.py`
- Create: `tests/fixtures/docs/sample_report.pdf` (generated, committed binary)

**Interfaces:**
- Produces: a committed single-page text PDF at `tests/fixtures/docs/sample_report.pdf` whose extractable text contains the exact strings `"Harbor Study Circle"` and `"Riverside Park"`. Consumed by the Docling and OCR tasks.

- [ ] **Step 1: Write the fixture generator**

Create `tests/fixtures/docs/make_sample_report.py`:

```python
"""Regenerate the committed sample_report.pdf fixture.

Run with the documents extra installed:
    uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,documents]' \
        -- python tests/fixtures/docs/make_sample_report.py
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF, provided by the `documents` extra

LINES = [
    "Synthetic evidence fixture for CRK local-stack tests.",
    "The Harbor Study Circle held its first meeting near Riverside Park.",
    "This document is authored test data and is not real evidence.",
]


def build(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in LINES:
        page.insert_text((72, y), line, fontsize=12)
        y += 20
    doc.save(str(path))
    doc.close()


if __name__ == "__main__":
    out = Path(__file__).parent / "sample_report.pdf"
    build(out)
    print(f"wrote {out}")
```

- [ ] **Step 2: Generate the committed PDF**

Run:
```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,documents]' \
    -- python tests/fixtures/docs/make_sample_report.py
```
Expected: prints `wrote .../tests/fixtures/docs/sample_report.pdf`; the file exists and is a few KB.

- [ ] **Step 3: Verify extractable text**

Run:
```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,documents]' \
    -- python -c "import fitz; print('Harbor Study Circle' in fitz.open('tests/fixtures/docs/sample_report.pdf')[0].get_text())"
```
Expected: `True`

- [ ] **Step 4: Write the README**

Create `tests/fixtures/docs/README.md`:

```markdown
# Document test fixtures

`sample_report.pdf` is a tiny, authored single-page PDF with a real text layer
used by the Docling parsing and OCRmyPDF smoke tests. Its extractable text
contains the markers `Harbor Study Circle` and `Riverside Park`.

Regenerate it deterministically with:

    uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,documents]' \
        -- python tests/fixtures/docs/make_sample_report.py

The content is synthetic test data, not real evidence.
```

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/docs/README.md tests/fixtures/docs/make_sample_report.py tests/fixtures/docs/sample_report.pdf
git commit -m "test(fixtures): add authored sample_report.pdf for local-stack tests"
```

---

### Task 2: Shared skip-guard + source-registration helpers

**Files:**
- Modify: `tests/helpers.py` (append helpers; keep existing content intact)

**Interfaces:**
- Produces (importable from `tests.helpers`):
  - `requires_extra(module_name: str) -> module` — thin wrapper over `pytest.importorskip`.
  - `requires_binary(name: str) -> None` — `pytest.skip` if `shutil.which(name)` is None.
  - `live_service(url: str | None, health_path: str) -> str` — returns the base URL if a fast GET to `url + health_path` succeeds; otherwise `pytest.skip`. Raising/connection error → skip.
  - `DOCS_FIXTURE: Path` — absolute path to `tests/fixtures/docs/sample_report.pdf`.
  - `register_pdf_source(case_dir: Path, source_id: str, pdf_path: Path) -> str` — copies `pdf_path` into `<case>/raw/sources/<source_id>.pdf`, appends a minimal source record to `records/sources.jsonl`, and returns the case-relative raw path.

- [ ] **Step 1: Write a failing test for the helpers**

Create `tests/runtime/integration/test_local_stack_helpers.py`:

```python
from pathlib import Path

import pytest

from tests import helpers
from crime_research_kit._runtime.core.casefile import find_source


def test_register_pdf_source_copies_and_records(synthetic_case_copy: Path):
    rel = helpers.register_pdf_source(synthetic_case_copy, "SFIX0001", helpers.DOCS_FIXTURE)
    assert rel == "raw/sources/SFIX0001.pdf"
    assert (synthetic_case_copy / rel).exists()
    source = find_source(synthetic_case_copy, "SFIX0001")
    assert source["raw_path"] == rel


def test_live_service_skips_when_unreachable():
    with pytest.raises(pytest.skip.Exception):
        helpers.live_service("http://127.0.0.1:9", "/readyz")


def test_requires_binary_skips_missing():
    with pytest.raises(pytest.skip.Exception):
        helpers.requires_binary("definitely-not-a-real-binary-xyz")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest tests/runtime/integration/test_local_stack_helpers.py -v`
Expected: FAIL with `AttributeError: module 'tests.helpers' has no attribute 'register_pdf_source'`.

- [ ] **Step 3: Implement the helpers**

Append to `tests/helpers.py` (add imports `import shutil`, `import httpx`, `import pytest` at top with the existing imports; reuse the existing `KIT_ROOT`):

```python
DOCS_FIXTURE = KIT_ROOT / "tests" / "fixtures" / "docs" / "sample_report.pdf"


def requires_extra(module_name: str):
    return pytest.importorskip(module_name)


def requires_binary(name: str) -> None:
    if shutil.which(name) is None:
        pytest.skip(f"required binary not on PATH: {name}")


def live_service(url: str | None, health_path: str) -> str:
    if not url:
        pytest.skip("live service URL not configured")
    base = url.rstrip("/")
    try:
        response = httpx.get(base + health_path, timeout=2.0)
        response.raise_for_status()
    except Exception as exc:  # connection refused, timeout, non-2xx
        pytest.skip(f"live service not reachable at {base}{health_path}: {exc}")
    return base


def register_pdf_source(case_dir, source_id: str, pdf_path):
    from pathlib import Path as _Path
    import shutil as _shutil

    from crime_research_kit._runtime.core.casefile import append_jsonl, record_path

    case_dir = _Path(case_dir)
    rel = f"raw/sources/{source_id}.pdf"
    dest = case_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    _shutil.copyfile(_Path(pdf_path), dest)
    append_jsonl(
        record_path(case_dir, "sources"),
        {
            "source_id": source_id,
            "title": f"Fixture source {source_id}",
            "source_type": "document",
            "raw_path": rel,
            "public_export": True,
            "reliability_grade": "C",
            "notes": "Synthetic fixture source; not real evidence.",
        },
    )
    return rel
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest tests/runtime/integration/test_local_stack_helpers.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add tests/helpers.py tests/runtime/integration/test_local_stack_helpers.py
git commit -m "test(helpers): add skip-guard and pdf-source-registration helpers"
```

---

### Task 3: Retrieval injection seam (production change)

**Files:**
- Modify: `src/crime_research_kit/_runtime/adapters/io/retrieval/index.py`
- Test: `tests/runtime/unit/sdk/test_retrieval_seam.py` (unit lane — pure signature/wiring, no deps required for the contract test)

**Interfaces:**
- Produces (public, keyword-only, all optional — defaults reproduce current behavior):
  - `index_case(case_dir, *, include_private=False, qdrant_url=None, collection=None, embed_model=None, client=None, embed=None) -> dict`
  - `query_case(case_dir, query, *, include_private=False, qdrant_url=None, collection=None, embed_model=None, top_k=8, client=None, embed=None) -> dict`
  - `client`: a pre-constructed Qdrant client (e.g. `QdrantClient(location=":memory:")`). When None, `QdrantClient(url=qdrant_url or DEFAULT_QDRANT_URL)` as today.
  - `embed`: a pre-constructed embedding object. When None, `HuggingFaceEmbedding(model_name=embed_model or DEFAULT_EMBED_MODEL)` as today.
  - Return shapes are unchanged.

- [ ] **Step 1: Write the failing contract test**

Create `tests/runtime/unit/sdk/test_retrieval_seam.py`:

```python
import inspect

from crime_research_kit._runtime.adapters.io.retrieval import index_case, query_case


def test_index_case_accepts_client_and_embed_seam():
    params = inspect.signature(index_case).parameters
    assert "client" in params and params["client"].default is None
    assert "embed" in params and params["embed"].default is None
    assert params["client"].kind is inspect.Parameter.KEYWORD_ONLY


def test_query_case_accepts_client_and_embed_seam():
    params = inspect.signature(query_case).parameters
    assert "client" in params and params["client"].default is None
    assert "embed" in params and params["embed"].default is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest tests/runtime/unit/sdk/test_retrieval_seam.py -v`
Expected: FAIL with `assert 'client' in params` (KeyError-style assertion failure).

- [ ] **Step 3: Add the seam to `index.py`**

Modify `index_case` signature and its `_build_index` call:

```python
def index_case(
    case_dir: str | Path,
    *,
    include_private: bool = False,
    qdrant_url: str | None = None,
    collection: str | None = None,
    embed_model: str | None = None,
    client=None,
    embed=None,
) -> dict[str, Any]:
    documents = build_evidence_documents(case_dir, include_private=include_private)
    embed_name = embed_model or DEFAULT_EMBED_MODEL
    index = _build_index(
        case_dir,
        documents,
        qdrant_url=qdrant_url or DEFAULT_QDRANT_URL,
        collection=collection,
        embed_model=embed_name,
        client=client,
        embed=embed,
    )
    return {
        "case_id": case_id(case_dir),
        "collection": _collection_name(case_dir, collection),
        "document_count": len(documents),
        "include_private": include_private,
        "index_type": type(index).__name__,
    }
```

Modify `query_case` signature and its `_build_index` call the same way (add `client=None, embed=None` params and pass `client=client, embed=embed` into `_build_index`).

Replace `_build_index` body:

```python
def _build_index(
    case_dir: str | Path,
    documents,
    *,
    qdrant_url: str,
    collection: str | None,
    embed_model: str,
    client=None,
    embed=None,
):
    try:
        from llama_index.core import Settings, StorageContext, VectorStoreIndex  # type: ignore
        from llama_index.vector_stores.qdrant import QdrantVectorStore  # type: ignore
        from qdrant_client import QdrantClient  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Install the local retrieval extra before indexing cases.") from exc

    if embed is None:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding  # type: ignore

        embed = HuggingFaceEmbedding(model_name=embed_model)
    Settings.embed_model = embed
    if client is None:
        client = QdrantClient(url=qdrant_url)
    vector_store = QdrantVectorStore(client=client, collection_name=_collection_name(case_dir, collection))
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_documents(to_llama_documents(documents), storage_context=storage_context)
```

Note: the `HuggingFaceEmbedding` import moves inside the `if embed is None` branch so injecting `embed` never triggers the heavy import.

- [ ] **Step 4: Run to verify it passes and LOC stays legal**

Run: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest tests/runtime/unit/sdk/test_retrieval_seam.py -v`
Expected: PASS (2 passed).

Run: `grep -vcE '^\s*(#|$)' src/crime_research_kit/_runtime/adapters/io/retrieval/index.py`
Expected: a number **< 200** (was 76; seam adds ~10).

- [ ] **Step 5: Run the existing retrieval-adjacent tests for regression**

Run: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest tests/runtime/integration/test_local_stack.py tests/runtime/unit/sdk/test_names_retrieval.py -v`
Expected: PASS (no behavior change).

- [ ] **Step 6: Commit**

```bash
git add src/crime_research_kit/_runtime/adapters/io/retrieval/index.py tests/runtime/unit/sdk/test_retrieval_seam.py
git commit -m "feat(retrieval): add client/embed injection seam to index/query_case"
```

---

### Task 4: Retrieval + Qdrant tests (hermetic + live, parametrized)

**Files:**
- Create: `tests/runtime/e2e/local_stack/README.md`
- Create: `tests/runtime/e2e/local_stack/conftest.py`
- Create: `tests/runtime/e2e/local_stack/test_retrieval.py`

**Interfaces:**
- Consumes: `index_case`, `query_case` (with `client`/`embed` seam from Task 3); `tests.helpers.live_service`, `requires_extra`; the `synthetic_case_copy` fixture from `tests/conftest.py`.
- Produces: a `qdrant_backend` fixture parametrized over `("memory", "live")` yielding a `QdrantClient`; the `live` param skips unless `CRK_QDRANT_URL` is reachable.

- [ ] **Step 1: Write the conftest (backend fixture + embedder helper)**

Create `tests/runtime/e2e/local_stack/conftest.py`:

```python
import os

import pytest

from tests import helpers


def _mock_embed():
    from llama_index.core.embeddings.mock_embed_model import MockEmbedding

    return MockEmbedding(embed_dim=16)


@pytest.fixture
def mock_embed():
    helpers.requires_extra("llama_index.core")
    return _mock_embed()


@pytest.fixture(params=["memory", "live"])
def qdrant_backend(request):
    helpers.requires_extra("qdrant_client")
    from qdrant_client import QdrantClient

    if request.param == "memory":
        client = QdrantClient(location=":memory:")
        yield client
        client.close()
        return
    base = helpers.live_service(os.environ.get("CRK_QDRANT_URL"), "/readyz")
    client = QdrantClient(url=base)
    yield client
    client.close()
```

If `MockEmbedding` is not importable at `llama_index.core.embeddings.mock_embed_model` in the pinned version, define a minimal fallback in this conftest: a `BaseEmbedding` subclass whose `_get_query_embedding`/`_get_text_embedding` return a deterministic fixed-length vector derived from `hash`-free character sums (avoid `hash()` — it is salted per process). Confirm the import path first with:
`uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,retrieval]' -- python -c "from llama_index.core.embeddings.mock_embed_model import MockEmbedding; print('ok')"`

- [ ] **Step 2: Write the parametrized round-trip test**

Create `tests/runtime/e2e/local_stack/test_retrieval.py`:

```python
import json
from pathlib import Path

from crime_research_kit._runtime.adapters.io.retrieval import index_case, query_case

COLLECTION = "crk_test_retrieval"


def _reset(client):
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)


def test_index_then_query_round_trip(synthetic_case_copy: Path, qdrant_backend, mock_embed):
    _reset(qdrant_backend)

    indexed = index_case(
        synthetic_case_copy,
        collection=COLLECTION,
        client=qdrant_backend,
        embed=mock_embed,
    )
    assert indexed["document_count"] > 0
    assert indexed["collection"] == COLLECTION

    result = query_case(
        synthetic_case_copy,
        "Harbor Study Circle",
        collection=COLLECTION,
        client=qdrant_backend,
        embed=mock_embed,
        top_k=5,
    )
    assert result["results"], "expected at least one retrieved node"
    first = result["results"][0]
    assert "score" in first and "text" in first and "metadata" in first
    _reset(qdrant_backend)


def test_private_records_excluded_by_default(synthetic_case_copy: Path, qdrant_backend, mock_embed):
    claims = synthetic_case_copy / "records" / "claims.jsonl"
    claims.write_text(
        claims.read_text(encoding="utf-8")
        + json.dumps(
            {
                "claim_id": "CPRIV",
                "claim": "Private review-only marker phrase.",
                "status": "unverified",
                "confidence": 0.1,
                "source_ids": ["SDEMO0001"],
                "public_export": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _reset(qdrant_backend)
    public = index_case(synthetic_case_copy, collection=COLLECTION, client=qdrant_backend, embed=mock_embed)
    _reset(qdrant_backend)
    private = index_case(
        synthetic_case_copy, collection=COLLECTION, include_private=True, client=qdrant_backend, embed=mock_embed
    )
    assert private["document_count"] > public["document_count"]
    _reset(qdrant_backend)
```

- [ ] **Step 3: Write the contract (degradation) test in the same file**

Append to `test_retrieval.py`:

```python
def test_index_case_without_retrieval_extra_raises(monkeypatch, synthetic_case_copy: Path):
    import sys

    # Simulate the retrieval extra being absent.
    monkeypatch.setitem(sys.modules, "llama_index.core", None)
    import pytest

    with pytest.raises(RuntimeError, match="retrieval extra"):
        index_case(synthetic_case_copy, collection=COLLECTION)
```

- [ ] **Step 4: Write the README**

Create `tests/runtime/e2e/local_stack/README.md`:

```markdown
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
```

Do **not** create an `__init__.py` here (see Global Constraints).

- [ ] **Step 5: Run the hermetic tier (memory param + contract)**

Run: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,retrieval]' -- python -m pytest tests/runtime/e2e/local_stack/test_retrieval.py -v`
Expected: the `[memory]` parametrizations PASS, the `[live]` parametrizations SKIP (no `CRK_QDRANT_URL`), the contract test PASSES. No failures.

- [ ] **Step 6: Commit**

```bash
git add tests/runtime/e2e/local_stack/
git commit -m "test(e2e): add hermetic+live parametrized retrieval/Qdrant round-trip"
```

---

### Task 5: Docling parsing smoke tests

**Files:**
- Create: `tests/quality/smoke/local_stack/README.md`
- Create: `tests/quality/smoke/local_stack/test_parsing.py`

**Interfaces:**
- Consumes: `parse_source` from `crime_research_kit._runtime.adapters.io.parsing.docling_parser`; `tests.helpers.register_pdf_source`, `DOCS_FIXTURE`, `requires_extra`; `synthetic_case_copy`.

- [ ] **Step 1: Write the hermetic + contract tests**

Create `tests/quality/smoke/local_stack/test_parsing.py`:

```python
import sys
from pathlib import Path

import pytest

from tests import helpers
from crime_research_kit._runtime.adapters.io.parsing.docling_parser import parse_source


def test_parse_source_extracts_text(synthetic_case_copy: Path):
    helpers.requires_extra("docling")
    helpers.register_pdf_source(synthetic_case_copy, "SPARSE1", helpers.DOCS_FIXTURE)

    result = parse_source(synthetic_case_copy, "SPARSE1")

    text_path = synthetic_case_copy / result["text_path"]
    assert text_path.exists()
    assert "Harbor Study Circle" in text_path.read_text(encoding="utf-8")
    assert result["skipped"] is False


def test_parse_source_is_idempotent(synthetic_case_copy: Path):
    helpers.requires_extra("docling")
    helpers.register_pdf_source(synthetic_case_copy, "SPARSE2", helpers.DOCS_FIXTURE)

    parse_source(synthetic_case_copy, "SPARSE2")
    again = parse_source(synthetic_case_copy, "SPARSE2")

    assert again["skipped"] is True


def test_parse_source_without_docling_raises(monkeypatch, synthetic_case_copy: Path):
    helpers.register_pdf_source(synthetic_case_copy, "SPARSE3", helpers.DOCS_FIXTURE)
    monkeypatch.setitem(sys.modules, "docling.document_converter", None)

    with pytest.raises(RuntimeError, match="[Dd]ocling"):
        parse_source(synthetic_case_copy, "SPARSE3")
```

- [ ] **Step 2: Write the README**

Create `tests/quality/smoke/local_stack/README.md`:

```markdown
# Local-stack smoke tests

Fast, hermetic smoke tests for the dependency-heavy local subsystems. Each test
skips cleanly when its optional extra or required binary is absent, so the default
lane stays green.

- `test_parsing.py` — Docling `parse_source` on the committed sample PDF.
- `test_ocr.py`     — OCRmyPDF `ocr_source` (requires `ocrmypdf`/`tesseract`/`gs`).
- `test_discovery.py` — SearXNG `discover_sources` against a mocked httpx transport.
```

Do **not** create an `__init__.py` here (see Global Constraints).

- [ ] **Step 3: Run the parsing tests**

Run: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,documents]' -- python -m pytest tests/quality/smoke/local_stack/test_parsing.py -v`
Expected: 3 passed (or the two docling tests SKIP if docling install is unavailable in the environment; the contract test still PASSES).

- [ ] **Step 4: Commit**

```bash
git add tests/quality/smoke/local_stack/README.md tests/quality/smoke/local_stack/test_parsing.py
git commit -m "test(smoke): add Docling parse_source hermetic + contract tests"
```

---

### Task 6: OCR smoke tests

**Files:**
- Create: `tests/quality/smoke/local_stack/test_ocr.py`

**Interfaces:**
- Consumes: `ocr_source` from `crime_research_kit._runtime.adapters.io.parsing.ocr`; `tests.helpers.register_pdf_source`, `DOCS_FIXTURE`, `requires_binary`; `synthetic_case_copy`.

- [ ] **Step 1: Write the hermetic + idempotency tests**

Create `tests/quality/smoke/local_stack/test_ocr.py`:

```python
from pathlib import Path

from tests import helpers
from crime_research_kit._runtime.adapters.io.parsing.ocr import ocr_source


def _require_ocr_binaries():
    for binary in ("ocrmypdf", "tesseract", "gs"):
        helpers.requires_binary(binary)


def test_ocr_source_writes_sidecar_and_pdf(synthetic_case_copy: Path):
    _require_ocr_binaries()
    helpers.register_pdf_source(synthetic_case_copy, "SOCR1", helpers.DOCS_FIXTURE)

    result = ocr_source(synthetic_case_copy, "SOCR1")

    sidecar = synthetic_case_copy / result["text_path"]
    output_pdf = synthetic_case_copy / result["ocr_pdf_path"]
    assert sidecar.exists()
    assert output_pdf.exists()


def test_ocr_source_is_idempotent(synthetic_case_copy: Path):
    _require_ocr_binaries()
    helpers.register_pdf_source(synthetic_case_copy, "SOCR2", helpers.DOCS_FIXTURE)

    ocr_source(synthetic_case_copy, "SOCR2")
    again = ocr_source(synthetic_case_copy, "SOCR2")

    assert again["skipped"] is True
```

- [ ] **Step 2: Run the OCR tests**

Run: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,documents]' -- python -m pytest tests/quality/smoke/local_stack/test_ocr.py -v`
Expected: 2 passed if `ocrmypdf`/`tesseract`/`gs` are installed; otherwise 2 SKIP. No failures either way.

- [ ] **Step 3: Commit**

```bash
git add tests/quality/smoke/local_stack/test_ocr.py
git commit -m "test(smoke): add OCRmyPDF ocr_source hermetic + idempotency tests"
```

---

### Task 7: SearXNG discovery — transport seam + smoke test

**Files:**
- Modify: `src/crime_research_kit/_runtime/adapters/io/acquisition/search.py` (add `_transport_for_tests` seam mirroring `http.py`)
- Create: `tests/quality/smoke/local_stack/test_discovery.py`

**Interfaces:**
- Produces: module-level `search._transport_for_tests: httpx.BaseTransport | None = None`, threaded into the `httpx.Client(...)` call. Production default `None` = unchanged behavior.
- Consumes: `discover_sources`; `synthetic_case_copy`.

Shape check: with no `__init__.py` (per Global Constraints), `tests/quality/smoke/local_stack/` ends at exactly 4 direct files — `README.md`, `test_parsing.py`, `test_ocr.py`, `test_discovery.py` — within the 1–4 cap.

- [ ] **Step 1: Write the failing discovery test**

Create `tests/quality/smoke/local_stack/test_discovery.py`:

```python
import json
from pathlib import Path

import httpx

from crime_research_kit._runtime.adapters.io.acquisition import search
from crime_research_kit._runtime.adapters.io.acquisition.search import discover_sources

SEARX_PAYLOAD = {
    "results": [
        {
            "title": "Harbor Study Circle archive",
            "url": "https://example.org/archive/1",
            "content": "Lead snippet about the Harbor Study Circle.",
            "engine": "duckduckgo",
            "score": 1.0,
        }
    ]
}


def test_discover_sources_writes_lead_only_report(monkeypatch, synthetic_case_copy: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["format"] == "json"
        return httpx.Response(200, json=SEARX_PAYLOAD)

    monkeypatch.setattr(search, "_transport_for_tests", httpx.MockTransport(handler))

    result = discover_sources(synthetic_case_copy, query="Harbor Study Circle")

    report = json.loads(Path(result["report"]).read_text(encoding="utf-8"))
    assert result["candidate_count"] == 1
    assert report["provider"] == "searxng"
    candidate = report["candidates"][0]
    assert candidate["lead_only"] is True
    assert candidate["url"] == "https://example.org/archive/1"
    # Safety contract: discovery creates leads only — no evidence, no records mutated.
    assert "claims" not in report
    assert report["notes"].startswith("Discovery candidates are leads only")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest tests/quality/smoke/local_stack/test_discovery.py -v`
Expected: FAIL — either `AttributeError: module ... has no attribute '_transport_for_tests'` or a real network attempt.

- [ ] **Step 3: Add the transport seam to `search.py`**

At module top (after `import httpx`), add:

```python
_transport_for_tests: httpx.BaseTransport | None = None
```

Change the client construction inside `discover_sources` from:

```python
    with httpx.Client(follow_redirects=True, timeout=30) as client:
```
to:
```python
    with httpx.Client(follow_redirects=True, timeout=30, transport=_transport_for_tests) as client:
```

- [ ] **Step 4: Run to verify it passes and LOC stays legal**

Run: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest tests/quality/smoke/local_stack/test_discovery.py -v`
Expected: PASS (1 passed).

Run: `grep -vcE '^\s*(#|$)' src/crime_research_kit/_runtime/adapters/io/acquisition/search.py`
Expected: `< 200`.

- [ ] **Step 5: Commit**

```bash
git add src/crime_research_kit/_runtime/adapters/io/acquisition/search.py tests/quality/smoke/local_stack/test_discovery.py
git commit -m "test(smoke): mock SearXNG discovery via httpx transport seam"
```

---

### Task 8: Self-hosted stack liveness (live e2e)

**Files:**
- Create: `tests/runtime/e2e/local_stack/test_stack_liveness.py`

**Interfaces:**
- Consumes: `tests.helpers.live_service`; env vars `CRK_QDRANT_URL`, `CRK_SEARXNG_URL`, `OLLAMA_HOST`.

- [ ] **Step 1: Write the liveness probes**

Create `tests/runtime/e2e/local_stack/test_stack_liveness.py`:

```python
import os

import httpx

from tests import helpers


def test_qdrant_ready():
    base = helpers.live_service(os.environ.get("CRK_QDRANT_URL"), "/readyz")
    assert httpx.get(base + "/readyz", timeout=5).status_code == 200


def test_searxng_search_json():
    base = helpers.live_service(os.environ.get("CRK_SEARXNG_URL"), "/healthz")
    response = httpx.get(base + "/search", params={"q": "crk", "format": "json"}, timeout=10)
    response.raise_for_status()
    assert "results" in response.json()


def test_ollama_tags():
    base = helpers.live_service(os.environ.get("OLLAMA_HOST"), "/api/tags")
    response = httpx.get(base + "/api/tags", timeout=10)
    response.raise_for_status()
    assert "models" in response.json()
```

Note: SearXNG exposes `/healthz`; if the deployed image lacks it, change the probe path to `/` (returns 200). Confirm against `deployment/searxng/settings.yml` behavior during live verification.

- [ ] **Step 2: Run (expect skips with no stack)**

Run: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest tests/runtime/e2e/local_stack/test_stack_liveness.py -v`
Expected: 3 SKIP (no live services configured). No failures.

- [ ] **Step 3: Commit**

```bash
git add tests/runtime/e2e/local_stack/test_stack_liveness.py
git commit -m "test(e2e): add Qdrant/SearXNG/Ollama liveness probes"
```

---

### Task 9: Full-lane verification, governance, and live proof

**Files:** none (verification only)

- [ ] **Step 1: Run the smoke lane**

Run: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,documents]' -- python -m pytest tests/quality/smoke -v`
Expected: existing `test_case_builder` passes; new local_stack smoke tests pass or skip (no failures).

- [ ] **Step 2: Run the e2e lane (hermetic)**

Run: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,retrieval]' -- python -m pytest tests/runtime/e2e -v`
Expected: existing e2e tests pass; retrieval `[memory]` passes; `[live]` and liveness SKIP.

- [ ] **Step 3: Run the governance shape check**

Run: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest tests/quality/governance/test_repository_shape.py -v`
Expected: PASS. If it flags `tests/quality/smoke/local_stack/` for file count, confirm no `__init__.py` was created and each new dir holds only its README + test files within 1–4.

- [ ] **Step 4: Run the compile/ledger check**

Run: `moon run crk:check`
Expected: PASS.

- [ ] **Step 5: Live proof — bring up Qdrant + SearXNG and run the live tier**

```bash
moon run crk:docker-up
# wait for services, then:
CRK_QDRANT_URL=http://localhost:6333 CRK_SEARXNG_URL=http://localhost:8080 \
  uv run --cache-dir .uv-cache --no-project --with-editable '.[dev,retrieval]' \
  -- python -m pytest tests/runtime/e2e/local_stack -v
```
Expected: retrieval `[live]` parametrizations PASS against real Qdrant; `test_qdrant_ready` and `test_searxng_search_json` PASS. `test_ollama_tags` passes only if Ollama is up and a model is pulled (`moon run crk:docker-pull-model`); otherwise it SKIPs — acceptable, hand the Ollama check to the operator if the model pull is impractical in-session.

- [ ] **Step 6: Tear down and final commit**

```bash
moon run crk:docker-down
git status --short
git log --oneline -9
```
Expected: only intended `test/*`-branch commits present; unrelated SDK files still unstaged. No further changes needed.

---

## Self-Review

**Spec coverage:**
- Layered posture (contract / hermetic / live) → Tasks 4–8 each carry all applicable tiers; skip-guards in Task 2. ✅
- Retrieval seam 3a → Task 3. ✅
- Retrieval hermetic + matching live test sharing one body → Task 4 (parametrized `qdrant_backend`). ✅
- Docling parse → Task 5; OCR → Task 6; SearXNG discovery → Task 7; stack liveness → Task 8. ✅
- Fixture PDF → Task 1. ✅
- Directory/shape rules, no new required deps, unchanged production behavior → Global Constraints + verified in Tasks 3/7/9. ✅
- Runner integration (auto-marker, no moon task change) → verified in Task 9. ✅

**Refinement flagged vs. spec:** the spec said the live retrieval test uses the *real* embedder. This plan uses `MockEmbedding` for *both* tiers and varies only the Qdrant client. Rationale: it isolates the real-Qdrant wire path as the thing under test, keeps the live run deterministic, and avoids a multi-GB HuggingFace model download. This is a strict improvement consistent with the spec's non-goal "not testing embedding accuracy." Confirm acceptance during review.

**Placeholder scan:** no TBD/TODO; every code step shows complete code. ✅

**Type consistency:** `client`/`embed` params are named identically across `index_case`, `query_case`, and `_build_index` (Task 3) and consumed with the same names in Task 4. `register_pdf_source`, `live_service`, `requires_extra`, `requires_binary`, `DOCS_FIXTURE` defined in Task 2 and used with matching signatures in Tasks 4–8. ✅

**Shape safety:** no new test directory gets an `__init__.py` (Global Constraints), matching sibling test dirs and keeping `tests/quality/smoke/local_stack/` at exactly 4 direct files. Verified in Task 9 Step 3.
