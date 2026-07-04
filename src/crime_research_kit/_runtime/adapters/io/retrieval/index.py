"""Local Qdrant-backed LlamaIndex integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crime_research_kit._runtime.core.casefile import case_id
from crime_research_kit._runtime.core.config import DEFAULT_EMBED_MODEL, DEFAULT_QDRANT_URL
from .documents import build_evidence_documents, to_llama_documents


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


def query_case(
    case_dir: str | Path,
    query: str,
    *,
    include_private: bool = False,
    qdrant_url: str | None = None,
    collection: str | None = None,
    embed_model: str | None = None,
    top_k: int = 8,
    client=None,
    embed=None,
) -> dict[str, Any]:
    index = _query_index(
        case_dir,
        qdrant_url=qdrant_url or DEFAULT_QDRANT_URL,
        collection=collection,
        embed_model=embed_model or DEFAULT_EMBED_MODEL,
        client=client,
        embed=embed,
    )
    retriever = index.as_retriever(similarity_top_k=top_k)
    results = []
    for item in retriever.retrieve(query):
        metadata = dict(item.node.metadata)
        if not include_private and metadata.get("public_export") is False:
            continue
        results.append({"score": item.score, "text": item.node.get_text(), "metadata": metadata})
    return {"query": query, "collection": _collection_name(case_dir, collection), "results": results}


def _backend(case_dir, *, qdrant_url, collection, embed_model, client, embed):
    """Resolve the embedder + Qdrant vector store shared by indexing and querying."""
    try:
        from llama_index.core import Settings, StorageContext, VectorStoreIndex  # type: ignore
        from llama_index.vector_stores.qdrant import QdrantVectorStore  # type: ignore
        from qdrant_client import QdrantClient  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Install the local retrieval extra before indexing cases.") from exc

    if embed is None:
        try:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install the local retrieval extra before indexing cases.") from exc

        embed = HuggingFaceEmbedding(model_name=embed_model)
    Settings.embed_model = embed
    if client is None:
        client = QdrantClient(url=qdrant_url)
    vector_store = QdrantVectorStore(client=client, collection_name=_collection_name(case_dir, collection))
    return StorageContext, VectorStoreIndex, vector_store, embed


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
    StorageContext, VectorStoreIndex, vector_store, _embed = _backend(
        case_dir, qdrant_url=qdrant_url, collection=collection, embed_model=embed_model, client=client, embed=embed
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_documents(to_llama_documents(documents), storage_context=storage_context)


def _query_index(
    case_dir: str | Path,
    *,
    qdrant_url: str,
    collection: str | None,
    embed_model: str,
    client=None,
    embed=None,
):
    """Attach to the existing Qdrant collection for retrieval WITHOUT re-embedding the corpus.

    ``index_case`` populates the collection; querying only needs to embed the query and
    search, so it connects via ``from_vector_store`` instead of re-inserting every document.
    """
    _StorageContext, VectorStoreIndex, vector_store, embed = _backend(
        case_dir, qdrant_url=qdrant_url, collection=collection, embed_model=embed_model, client=client, embed=embed
    )
    return VectorStoreIndex.from_vector_store(vector_store, embed_model=embed)


def _collection_name(case_dir: str | Path, collection: str | None) -> str:
    return collection or f"crk_evidence_{case_id(case_dir)}"
