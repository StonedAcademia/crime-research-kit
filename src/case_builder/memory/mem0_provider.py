"""Mem0 OSS workflow memory provider configured for local infrastructure."""

from __future__ import annotations

from typing import Any

from ..casefile import case_id
from .base import MemoryEntry


class Mem0LocalProvider:
    """Persist workflow memory through Mem0 using local Qdrant and local models."""

    def __init__(
        self,
        case_dir: str,
        *,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        llm_provider: str = "ollama",
        llm_model: str = "llama3.1",
        embedder_provider: str = "huggingface",
        embedder_model: str = "BAAI/bge-small-en-v1.5",
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
                    "host": qdrant_host,
                    "port": qdrant_port,
                    "collection_name": f"trcr_memory_{self.user_id}",
                },
            },
            "llm": {"provider": llm_provider, "config": {"model": llm_model, "temperature": 0.1}},
            "embedder": {"provider": embedder_provider, "config": {"model": embedder_model}},
        }
        self.memory = Memory.from_config(config)

    def add(self, entry: MemoryEntry) -> dict[str, Any]:
        metadata = {"evidence": False, **entry.metadata}
        result = self.memory.add(entry.text, user_id=self.user_id, metadata=metadata)
        return {"provider": "mem0", "result": result, "text": entry.text}
