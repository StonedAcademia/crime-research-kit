"""Mem0 OSS workflow memory provider configured for local infrastructure."""

from __future__ import annotations

from typing import Any

from ..casefile import case_id
from ..config import embed_model as default_embed_model
from ..config import embedder_provider as default_embedder_provider
from ..config import mem0_llm_model as default_mem0_llm_model
from ..config import mem0_llm_provider as default_mem0_llm_provider
from ..config import qdrant_host as default_qdrant_host
from ..config import qdrant_port as default_qdrant_port
from .base import MemoryEntry


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
                    "host": default_qdrant_host(qdrant_host),
                    "port": default_qdrant_port(qdrant_port),
                    "collection_name": f"crk_memory_{self.user_id}",
                },
            },
            "llm": {
                "provider": default_mem0_llm_provider(llm_provider),
                "config": {"model": default_mem0_llm_model(llm_model), "temperature": 0.1},
            },
            "embedder": {
                "provider": default_embedder_provider(embedder_provider),
                "config": {"model": default_embed_model(embedder_model)},
            },
        }
        self.memory = Memory.from_config(config)

    def add(self, entry: MemoryEntry) -> dict[str, Any]:
        metadata = {"evidence": False, **entry.metadata}
        result = self.memory.add(entry.text, user_id=self.user_id, metadata=metadata)
        return {"provider": "mem0", "result": result, "text": entry.text}
