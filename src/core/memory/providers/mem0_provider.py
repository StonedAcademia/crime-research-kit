"""Mem0 OSS workflow memory provider configured for local infrastructure."""

from __future__ import annotations

from typing import Any

from core.casefile import case_id
from core.config import (
    DEFAULT_EMBED_MODEL,
    DEFAULT_EMBEDDER_PROVIDER,
    DEFAULT_MEM0_LLM_MODEL,
    DEFAULT_MEM0_LLM_PROVIDER,
    DEFAULT_QDRANT_HOST,
    DEFAULT_QDRANT_PORT,
)
from core.memory.base import MemoryEntry


class Mem0LocalProvider:
    """Persist workflow memory through Mem0 using local Qdrant and local models."""

    def __init__(
        self,
        case_dir: str,
        *,
        qdrant_host: str | None = None,
        qdrant_port: int | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        embedder_provider: str | None = None,
        embedder_model: str | None = None,
    ) -> None:
        try:
            from mem0 import Memory  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Mem0 is not installed. Install the local memory extra.") from exc
        self.user_id = case_id(case_dir)
        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "host": qdrant_host or DEFAULT_QDRANT_HOST,
                    "port": qdrant_port if qdrant_port is not None else DEFAULT_QDRANT_PORT,
                    "collection_name": f"crk_memory_{self.user_id}",
                },
            },
            "llm": {
                "provider": llm_provider or DEFAULT_MEM0_LLM_PROVIDER,
                "config": {"model": llm_model or DEFAULT_MEM0_LLM_MODEL, "temperature": 0.1},
            },
            "embedder": {
                "provider": embedder_provider or DEFAULT_EMBEDDER_PROVIDER,
                "config": {"model": embedder_model or DEFAULT_EMBED_MODEL},
            },
        }
        self.memory = Memory.from_config(config)

    def add(self, entry: MemoryEntry) -> dict[str, Any]:
        metadata = {"evidence": False, **entry.metadata}
        result = self.memory.add(entry.text, user_id=self.user_id, metadata=metadata)
        return {"provider": "mem0", "result": result, "text": entry.text}
