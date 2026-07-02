"""Runtime defaults for self-hosted CRK services, resolved once at process boundaries."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MODEL_SPEC = "ollama:llama3.1"
DEFAULT_SEARXNG_URL = "http://localhost:8080"
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_QDRANT_HOST = "localhost"
DEFAULT_QDRANT_PORT = 6333
DEFAULT_EMBED_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_MEM0_LLM_PROVIDER = "ollama"
DEFAULT_MEM0_LLM_MODEL = "llama3.1"
DEFAULT_EMBEDDER_PROVIDER = "huggingface"


class CrkSettings(BaseSettings):
    """Environment-backed service configuration. Construct once at CLI/MCP startup."""

    model_config = SettingsConfigDict(protected_namespaces=(), extra="ignore")

    model_spec: str = Field(default=DEFAULT_MODEL_SPEC, validation_alias="CRK_MODEL")
    searxng_url: str = Field(default=DEFAULT_SEARXNG_URL, validation_alias="CRK_SEARXNG_URL")
    qdrant_url: str = Field(default=DEFAULT_QDRANT_URL, validation_alias="CRK_QDRANT_URL")
    qdrant_host: str = Field(default=DEFAULT_QDRANT_HOST, validation_alias="CRK_QDRANT_HOST")
    qdrant_port: int = Field(default=DEFAULT_QDRANT_PORT, validation_alias="CRK_QDRANT_PORT")
    embed_model: str = Field(default=DEFAULT_EMBED_MODEL, validation_alias="CRK_EMBED_MODEL")
    mem0_llm_provider: str = Field(default=DEFAULT_MEM0_LLM_PROVIDER, validation_alias="CRK_MEM0_LLM_PROVIDER")
    mem0_llm_model: str = Field(default=DEFAULT_MEM0_LLM_MODEL, validation_alias="CRK_MEM0_LLM_MODEL")
    embedder_provider: str = Field(default=DEFAULT_EMBEDDER_PROVIDER, validation_alias="CRK_EMBEDDER_PROVIDER")
