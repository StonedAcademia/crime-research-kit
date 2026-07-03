"""Workflow facade for the public SDK."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .context import CrkContext
from .errors import DEPENDENCY_MISSING, INVALID_INPUT, OPERATION_FAILED
from .operations import get_operation
from .requests import PathValue, RunnerName, WorkflowPlanRequest, WorkflowResumeRequest
from .results import OperationResult

_RUNNERS = {"auto", "langgraph", "sequential"}


@dataclass(frozen=True, slots=True)
class WorkflowClient:
    """App workflow operations exposed through the SDK."""

    context: CrkContext

    def plan(self, case_dir: PathValue | WorkflowPlanRequest | None = None, **kwargs: Any) -> OperationResult:
        """Plan or execute the initial case-builder workflow."""
        request = case_dir if isinstance(case_dir, WorkflowPlanRequest) else WorkflowPlanRequest(case_dir=case_dir, **kwargs)
        operation = _op("workflows.plan")
        resolved = _case_dir(self.context, request.case_dir)
        if resolved is None:
            return _invalid(operation, "case_dir is required")
        if request.runner not in _RUNNERS:
            return _invalid(operation, f"runner must be one of {sorted(_RUNNERS)}", str(resolved))
        try:
            from crime_research_kit._runtime.core.models.state import CaseBuilderState
            from crime_research_kit._runtime.pipeline.app.service import run_case_builder

            state = CaseBuilderState(
                case_dir=str(resolved),
                title=request.title,
                subject=request.subject,
                lanes=list(request.lanes),
                source_urls=list(request.source_urls),
                source_ids=list(request.source_ids),
                index_enabled=request.index,
                thread_id=request.thread_id,
                llm_enabled=request.llm,
            )
            raw = run_case_builder(
                state,
                execute=_execute(self.context, request.execute),
                runner=request.runner,
                checkpoint=request.checkpoint,
                model_spec=request.model_spec or _setting(self.context, "model_spec"),
                qdrant_url=request.qdrant_url or _setting(self.context, "qdrant_url"),
                embed_model=request.embed_model or _setting(self.context, "embed_model"),
                repo_root=self.context.repo_root,
            )
        except Exception as exc:
            return _exception_result(operation, exc, case_ref=str(resolved))
        return _result(operation, raw, case_ref=str(resolved))

    def resume(self, case_dir: PathValue | WorkflowResumeRequest | None = None, **kwargs: Any) -> OperationResult:
        """Resume a checkpointed case-builder workflow with review decisions."""
        request = case_dir if isinstance(case_dir, WorkflowResumeRequest) else WorkflowResumeRequest(case_dir=case_dir, **kwargs)
        operation = _op("workflows.resume")
        resolved = _case_dir(self.context, request.case_dir)
        if resolved is None:
            return _invalid(operation, "case_dir is required")
        if not request.thread_id:
            return _invalid(operation, "thread_id is required", str(resolved))
        try:
            from crime_research_kit._runtime.pipeline.app.service import resume_case_builder

            raw = resume_case_builder(
                str(resolved),
                thread_id=request.thread_id,
                approved_packets=list(request.approved_packets),
                rejected_packets=_rejected(request.rejected_packets, request.reject_reason),
                export_approved=request.export_approved,
                execute=_execute(self.context, request.execute),
                llm=request.llm,
                model_spec=request.model_spec or _setting(self.context, "model_spec"),
                qdrant_url=request.qdrant_url or _setting(self.context, "qdrant_url"),
                embed_model=request.embed_model or _setting(self.context, "embed_model"),
                repo_root=self.context.repo_root,
            )
        except Exception as exc:
            return _exception_result(operation, exc, case_ref=str(resolved))
        return _result(operation, raw, case_ref=str(resolved))


def _op(name: str) -> str:
    return get_operation(name).name


def _case_dir(context: CrkContext, case_dir: PathValue | None) -> Path | None:
    return context.resolve_case_ref(case_dir)


def _execute(context: CrkContext, requested: bool) -> bool:
    return requested and not context.dry_run


def _setting(context: CrkContext, key: str) -> str | None:
    value = context.settings.get(key)
    return str(value) if value else None


def _result(operation: str, raw: Mapping[str, Any], *, case_ref: str) -> OperationResult:
    data = dict(raw)
    errors = [
        {"code": OPERATION_FAILED, "message": str(message), "operation": operation, "case_ref": case_ref}
        for message in data.get("errors", []) or []
    ]
    return OperationResult(
        ok=not errors,
        operation=operation,
        case_ref=case_ref,
        data=data,
        errors=errors,
        counts=_counts(data),
        diagnostics=_diagnostics(data),
    )


def _invalid(operation: str, message: str, case_ref: str | None = None) -> OperationResult:
    return OperationResult.failure(operation, {"code": INVALID_INPUT, "message": message}, case_ref=case_ref)


def _exception_result(operation: str, exc: Exception, *, case_ref: str) -> OperationResult:
    return OperationResult.failure(
        operation,
        {"code": _exception_code(exc), "message": str(exc), "operation": operation, "case_ref": case_ref},
        case_ref=case_ref,
    )


def _exception_code(exc: Exception) -> str:
    message = str(exc)
    if isinstance(exc, (ImportError, ModuleNotFoundError)) or "LangGraph is not installed" in message:
        return DEPENDENCY_MISSING
    if "Checkpointing requires" in message:
        return INVALID_INPUT
    return OPERATION_FAILED


def _counts(data: Mapping[str, Any]) -> dict[str, int]:
    names = ("lanes", "source_urls", "source_ids", "packets", "approved_packets", "rejected_packets", "tool_results")
    return {name: len(data[name]) for name in names if isinstance(data.get(name), list)}


def _diagnostics(data: Mapping[str, Any]) -> dict[str, Any]:
    return {name: data[name] for name in ("runner", "thread_id", "paused_before", "status") if name in data}


def _rejected(items: Sequence[str | Mapping[str, Any]], reason: str | None) -> list[dict[str, Any]]:
    return [dict(item) if isinstance(item, Mapping) else {"packet": str(item), "reason": reason} for item in items]


__all__ = ["WorkflowClient", "WorkflowPlanRequest", "WorkflowResumeRequest"]
