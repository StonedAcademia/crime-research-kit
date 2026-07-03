"""Retrieval wrappers for the public SDK."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .cases import _from_op_result
from .context import CrkContext
from .errors import DEPENDENCY_MISSING, NETWORK_FAILED, OPERATION_FAILED
from .operations import get_operation
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
        from adapters.ops import query as query_ops

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


def _op(name: str) -> str:
    return get_operation(name).name


def _setting(context: CrkContext, key: str) -> str | None:
    value = context.settings.get(key)
    return str(value) if value else None


def _exception_result(operation: str, exc: Exception, *, case_ref: str) -> OperationResult:
    return OperationResult.failure(
        operation,
        {"code": _exception_code(exc), "message": str(exc), "operation": operation, "case_ref": case_ref},
        case_ref=case_ref,
    )


def _exception_code(exc: Exception) -> str:
    lowered = str(exc).lower()
    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return DEPENDENCY_MISSING
    if exc.__class__.__module__.startswith("httpx") or "connection" in lowered:
        return NETWORK_FAILED
    return OPERATION_FAILED


__all__ = ["CaseRetrievalClient"]
