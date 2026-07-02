"""Runtime defaults for self-hosted CRK services."""

from __future__ import annotations

import os

DEFAULT_MODEL_SPEC = "ollama:llama3.1"
DEFAULT_SEARXNG_URL = "http://localhost:8080"
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_QDRANT_HOST = "localhost"
DEFAULT_QDRANT_PORT = 6333
DEFAULT_EMBED_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_MEM0_LLM_PROVIDER = "ollama"
DEFAULT_MEM0_LLM_MODEL = "llama3.1"
DEFAULT_EMBEDDER_PROVIDER = "huggingface"


def env_str(name: str, default: str) -> str:
    return os.environ.get(name) or default


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw else default


def model_spec(value: str | None = None) -> str:
    return value or env_str("CRK_MODEL", DEFAULT_MODEL_SPEC)


def searxng_url(value: str | None = None) -> str:
    return value or env_str("CRK_SEARXNG_URL", DEFAULT_SEARXNG_URL)


def qdrant_url(value: str | None = None) -> str:
    return value or env_str("CRK_QDRANT_URL", DEFAULT_QDRANT_URL)


def qdrant_host(value: str | None = None) -> str:
    return value or env_str("CRK_QDRANT_HOST", DEFAULT_QDRANT_HOST)


def qdrant_port(value: int | None = None) -> int:
    return value if value is not None else env_int("CRK_QDRANT_PORT", DEFAULT_QDRANT_PORT)


def embed_model(value: str | None = None) -> str:
    return value or env_str("CRK_EMBED_MODEL", DEFAULT_EMBED_MODEL)


def mem0_llm_provider(value: str | None = None) -> str:
    return value or env_str("CRK_MEM0_LLM_PROVIDER", DEFAULT_MEM0_LLM_PROVIDER)


def mem0_llm_model(value: str | None = None) -> str:
    return value or env_str("CRK_MEM0_LLM_MODEL", DEFAULT_MEM0_LLM_MODEL)


def embedder_provider(value: str | None = None) -> str:
    return value or env_str("CRK_EMBEDDER_PROVIDER", DEFAULT_EMBEDDER_PROVIDER)
