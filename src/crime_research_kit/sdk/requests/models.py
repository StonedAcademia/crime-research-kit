"""Strict request models for public SDK operations."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, create_model

from ..operations import OperationSpec, list_operations

PathValue: TypeAlias = str | Path
RunnerName: TypeAlias = Literal["auto", "langgraph", "sequential"]
Fields = dict[str, tuple[Any, Any]]


class OperationRequest(BaseModel):
    """Base class for strict SDK request models."""

    model_config = ConfigDict(extra="forbid", frozen=True)


_F: dict[str, Fields] = {
    "CreateCaseRequest": {"slug": (str, ...), "title": (str | None, None), "subject": (str | None, None)},
    "ListCasesRequest": {},
    "CaseInfoRequest": {"include_private": (bool | None, None)},
    "ListRecordsRequest": {"record_type": (str, ...), "include_private": (bool | None, None), "limit": (int | None, None)},
    "SourceTextRequest": {"source_id": (str, ...), "include_private": (bool | None, None), "max_chars": (int | None, None)},
    "AddSourceRequest": {
        "title": (str, ...),
        "url": (str | None, None),
        "source_type": (str | None, None),
        "public_export": (bool, True),
        "metadata": (dict[str, Any] | None, None),
    },
    "IngestUrlRequest": {
        "url": (str, ...),
        "title": (str | None, None),
        "source_type": (str | None, None),
        "public_export": (bool, True),
        "metadata": (dict[str, Any] | None, None),
    },
    "DiscoverSourcesRequest": {
        "query": (str, ...),
        "searxng_url": (str | None, None),
        "limit": (int, Field(default=10, ge=1)),
        "out": (str | None, None),
    },
    "ParseSourceRequest": {"source_id": (str, ...), "force": (bool, False)},
    "OcrSourceRequest": {"source_id": (str, ...), "language": (str, "eng"), "force": (bool, False)},
    "PreserveSourceRequest": {
        "source_id": (str, ...),
        "archive_url": (str | None, None),
        "content_type": (str | None, None),
        "out": (str | None, None),
    },
    "DraftExtractionRequest": {
        "source_id": (str, ...),
        "template": (str, "generic"),
        "excerpt_chars": (int, Field(default=6000, ge=1)),
    },
    "ListExtractionsRequest": {},
    "ReadExtractionRequest": {"packet_name": (str, ...)},
    "SaveExtractionRequest": {"packet_name": (str, ...), "packet": (dict[str, Any], ...)},
    "ImportReviewedExtractionRequest": {"packet_name": (str, ...), "approved": (bool, False)},
    "NerSuggestRequest": {"source_id": (str | None, None), "limit": (int, Field(default=80, ge=1))},
    "LinkNamesRequest": {"names": (tuple[str, ...], Field(default_factory=tuple)), "names_file": (str | None, None)},
    "PlanPublicRecordsRequest": {"subject": (str, ...), "lanes": (tuple[str, ...], Field(default_factory=tuple))},
    "IndexTranscriptRequest": {"source_id": (str | None, None), "out": (str | None, None)},
    "PlanOpenRecordsRequest": {"subject": (str, ...), "lanes": (tuple[str, ...], Field(default_factory=tuple))},
    "ValidateCaseRequest": {},
    "DedupeRecordsRequest": {
        "record_type": (str, "all"),
        "min_key_chars": (int, Field(default=12, ge=1)),
        "out": (str | None, None),
    },
    "ResolveIdentitiesRequest": {
        "min_key_chars": (int, Field(default=8, ge=1)),
        "include_merged": (bool, False),
        "out": (str | None, None),
    },
    "AuditContradictionsRequest": {
        "include_private": (bool | None, None),
        "min_overlap": (float, 0.45),
        "fail_on_flags": (bool, False),
        "out": (str | None, None),
    },
    "NarrativeReadinessRequest": {
        "include_private": (bool | None, None),
        "require_spans": (bool, False),
        "min_independent_sources": (int, Field(default=2, ge=1)),
        "fail_on_blockers": (bool, False),
        "out": (str | None, None),
    },
    "AuditPrivacyRedactionsRequest": {
        "include_private": (bool | None, None),
        "require_redaction_log": (bool, False),
        "warn_only": (bool, False),
        "out": (str | None, None),
    },
    "AuditPublicExportRequest": {"warn_only": (bool, False), "out": (str | None, None)},
    "AuditSourceIndependenceRequest": {
        "include_private": (bool | None, None),
        "min_title_chars": (int, Field(default=16, ge=1)),
        "fail_on_flags": (bool, False),
        "out": (str | None, None),
    },
    "ExportManimRequest": {"include_private": (bool | None, None)},
    "ExportTimelineRequest": {"cases_root": (PathValue | None, None), "include_private": (bool | None, None), "out_dir": (str | None, None)},
    "ExportCaseVisualsRequest": {"include_private": (bool | None, None), "out_dir": (str | None, None)},
    "WorkflowPlanRequest": {
        "case_dir": (PathValue | None, None),
        "title": (str | None, None),
        "subject": (str | None, None),
        "lanes": (list[str], Field(default_factory=list)),
        "source_urls": (list[str], Field(default_factory=list)),
        "source_ids": (list[str], Field(default_factory=list)),
        "index": (bool, False),
        "thread_id": (str | None, None),
        "execute": (bool, False),
        "runner": (RunnerName, "auto"),
        "checkpoint": (bool, False),
        "llm": (bool, False),
        "model_spec": (str | None, None),
        "qdrant_url": (str | None, None),
        "embed_model": (str | None, None),
    },
    "WorkflowResumeRequest": {
        "case_dir": (PathValue | None, None),
        "thread_id": (str, ""),
        "approved_packets": (list[str], Field(default_factory=list)),
        "rejected_packets": (list[str | dict[str, Any]], Field(default_factory=list)),
        "reject_reason": (str | None, None),
        "export_approved": (bool, False),
        "execute": (bool, False),
        "llm": (bool, False),
        "model_spec": (str | None, None),
        "qdrant_url": (str | None, None),
        "embed_model": (str | None, None),
    },
    "IndexCaseRequest": {
        "include_private": (bool | None, None),
        "qdrant_url": (str | None, None),
        "collection": (str | None, None),
        "embed_model": (str | None, None),
    },
    "QueryCaseRequest": {
        "query_text": (str, ...),
        "include_private": (bool | None, None),
        "qdrant_url": (str | None, None),
        "collection": (str | None, None),
        "embed_model": (str | None, None),
        "top_k": (int, Field(default=8, ge=1)),
    },
    "RememberResearchActionsRequest": {"actions": (tuple[str, ...], Field(default_factory=tuple)), "provider": (str | None, None)},
}


def _build_models() -> Mapping[str, type[OperationRequest]]:
    specs = {spec.request_model: spec for spec in list_operations()}
    missing = set(specs) - set(_F)
    if missing:
        raise RuntimeError(f"Missing SDK request models: {sorted(missing)}")
    models: dict[str, type[OperationRequest]] = {}
    for name in sorted(specs):
        fields = dict(_F[name])
        if specs[name].requires_case:
            fields.setdefault("case_ref", (PathValue | None, None))
            fields.setdefault("case_dir", (PathValue | None, None))
        models[name] = create_model(name, __base__=OperationRequest, __module__=__name__, **fields)
    return MappingProxyType(models)


REQUEST_MODELS = _build_models()
globals().update(REQUEST_MODELS)


def get_request_model(model_or_operation: str | OperationSpec) -> type[OperationRequest]:
    """Return the strict request model for a catalog model or operation name."""
    return REQUEST_MODELS[_model_name(model_or_operation)]


def validate_request(model_or_operation: str | OperationSpec, payload: Mapping[str, Any] | OperationRequest | None = None, **kwargs: Any) -> OperationRequest:
    """Validate payload data against a strict SDK request model."""
    model = get_request_model(model_or_operation)
    if isinstance(payload, model) and not kwargs:
        return payload
    data = payload.model_dump() if isinstance(payload, OperationRequest) else dict(payload or {})
    data.update(kwargs)
    return model.model_validate(data)


def _model_name(model_or_operation: str | OperationSpec) -> str:
    if isinstance(model_or_operation, OperationSpec):
        return model_or_operation.request_model
    if model_or_operation in REQUEST_MODELS:
        return model_or_operation
    from ..operations import get_operation

    return get_operation(model_or_operation).request_model


__all__ = [
    "OperationRequest",
    "PathValue",
    "REQUEST_MODELS",
    "RunnerName",
    "get_request_model",
    "validate_request",
    *tuple(REQUEST_MODELS),
]
