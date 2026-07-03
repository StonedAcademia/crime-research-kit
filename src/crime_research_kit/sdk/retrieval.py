"""Retrieval wrappers for the public SDK."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ._internal import exception_result as _exception_result
from ._internal import from_op_result as _from_op_result
from ._internal import operation_name as _op
from ._internal import setting as _setting
from .context import CrkContext
from .results import OperationResult


@dataclass(frozen=True, slots=True)
class CaseRetrievalClient:
    """Local retrieval index operations for one case."""

    context: CrkContext
    case_ref: Path

    @property
    def case_dir(self) -> Path:
        resolved = self.context.resolve_case_ref(self.case_ref)
        if resolved is None:
            raise ValueError("CaseRetrievalClient requires a case reference.")
        return resolved

    def query(
        self,
        query_text: str,
        *,
        include_private: bool | None = None,
        qdrant_url: str | None = None,
        collection: str | None = None,
        embed_model: str | None = None,
        top_k: int = 8,
    ) -> OperationResult:
        """Query the local retrieval index for a case."""
        from crime_research_kit._runtime.adapters.ops import query as query_ops

        operation = _op("retrieval.query")
        try:
            raw = query_ops.query_case(
                str(self.case_dir),
                query_text,
                include_private=self._include_private(include_private),
                qdrant_url=qdrant_url or _setting(self.context, "qdrant_url"),
                collection=collection,
                embed_model=embed_model or _setting(self.context, "embed_model"),
                top_k=top_k,
            )
        except Exception as exc:
            return _exception_result(operation, exc, case_ref=str(self.case_dir))
        return _from_op_result(operation, raw, case_ref=str(self.case_dir))

    def _include_private(self, explicit: bool | None) -> bool:
        return self.context.include_private if explicit is None else explicit


__all__ = ["CaseRetrievalClient"]
