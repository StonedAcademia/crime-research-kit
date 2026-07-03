"""Private helpers shared by SDK wrapper modules."""

from __future__ import annotations

from typing import Any

from .context import CrkContext
from .errors import (
    CASE_NOT_FOUND,
    DEPENDENCY_MISSING,
    INVALID_INPUT,
    NETWORK_FAILED,
    OPERATION_FAILED,
    PRIVACY_BLOCKED,
    SAFETY_BLOCKED,
    SOURCE_NOT_FOUND,
)
from .operations import get_operation
from .results import OperationResult


def operation_name(name: str) -> str:
    """Return the catalog-normalized operation name."""
    return get_operation(name).name


def runner(context: CrkContext):
    """Build the private runtime runner for subprocess-backed operations."""
    from crime_research_kit._runtime.adapters.ops.runner import CrkRunner

    return CrkRunner(repo_root=context.repo_root, dry_run=context.dry_run)


def setting(context: CrkContext, key: str) -> str | None:
    """Read a string setting from the SDK context."""
    value = context.settings.get(key)
    return str(value) if value else None


def from_op_result(operation: str, raw: Any, *, case_ref: str | None = None) -> OperationResult:
    """Convert a private runtime OpResult-like object into the SDK result envelope."""
    data = dict(getattr(raw, "data", {}) or {})
    return OperationResult(
        ok=bool(getattr(raw, "ok", False)),
        operation=operation,
        case_ref=case_ref,
        data=data,
        errors=[
            {
                "code": error_code(message),
                "message": message,
                "operation": operation,
                "case_ref": case_ref,
            }
            for message in getattr(raw, "errors", []) or []
        ],
        warnings=[
            {"message": message, "operation": operation, "case_ref": case_ref}
            for message in getattr(raw, "warnings", []) or []
        ],
        counts=_counts_for(operation, data),
        diagnostics=_diagnostics(raw),
    )


def invalid_result(operation: str, message: str, case_ref: str | None = None) -> OperationResult:
    """Return a standardized SDK input-error result."""
    return OperationResult.failure(operation, {"code": INVALID_INPUT, "message": message}, case_ref=case_ref)


def exception_result(operation: str, exc: Exception, *, case_ref: str) -> OperationResult:
    """Return a standardized SDK result for runtime exceptions."""
    return OperationResult.failure(
        operation,
        {
            "code": exception_code(exc),
            "message": str(exc),
            "operation": operation,
            "case_ref": case_ref,
        },
        case_ref=case_ref,
    )


def exception_code(exc: Exception) -> str:
    """Map common runtime exceptions to public SDK error codes."""
    message = str(exc)
    lowered = message.lower()
    if "Checkpointing requires" in message:
        return INVALID_INPUT
    if isinstance(exc, (ImportError, ModuleNotFoundError, FileNotFoundError)):
        return DEPENDENCY_MISSING
    if "LangGraph is not installed" in message or "not installed" in lowered or "ocrmypdf" in lowered:
        return DEPENDENCY_MISSING
    if exc.__class__.__module__.startswith("httpx") or "connection" in lowered:
        return NETWORK_FAILED
    if message.startswith("Source not found"):
        return SOURCE_NOT_FOUND
    if "raw_path" in lowered:
        return INVALID_INPUT
    return OPERATION_FAILED


def error_code(message: str) -> str:
    """Map runtime OpResult error strings to public SDK error codes."""
    if "Not a CRK case workspace" in message:
        return CASE_NOT_FOUND
    if message.startswith("Source not found"):
        return SOURCE_NOT_FOUND
    if message.startswith(("Extraction packet must", "Packet not found")):
        return INVALID_INPUT
    if "public_export=false" in message:
        return PRIVACY_BLOCKED
    if "confirm=True" in message or "guilt-implying label" in message:
        return SAFETY_BLOCKED
    if "Automated writes must stay under" in message or "outside the case workspace" in message:
        return SAFETY_BLOCKED
    if message.startswith("Unknown record type"):
        return INVALID_INPUT
    return OPERATION_FAILED


def _counts_for(operation: str, data: dict[str, Any]) -> dict[str, int]:
    if operation == "case.info":
        return {key: int(value) for key, value in data.get("record_counts", {}).items()}
    return {key: int(data[key]) for key in ("count", "filtered") if isinstance(data.get(key), int)}


def _diagnostics(raw: Any) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {}
    for name in ("command", "stdout", "stderr"):
        value = getattr(raw, name, None)
        if value:
            diagnostics[name] = value
    for name in ("dry_run", "skipped"):
        value = getattr(raw, name, False)
        if value:
            diagnostics[name] = value
    returncode = getattr(raw, "returncode", 0)
    if returncode:
        diagnostics["returncode"] = returncode
    return diagnostics


__all__ = [
    "error_code",
    "exception_code",
    "exception_result",
    "from_op_result",
    "invalid_result",
    "operation_name",
    "runner",
    "setting",
]
