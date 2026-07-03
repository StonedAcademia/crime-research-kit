"""Case and record read surfaces for the public SDK."""

from __future__ import annotations

from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Any

from .context import CrkContext
from .errors import CASE_NOT_FOUND, INVALID_INPUT, OPERATION_FAILED, PRIVACY_BLOCKED, SAFETY_BLOCKED, SOURCE_NOT_FOUND
from .results import OperationResult

CaseRef = str | PathLike[str] | Path


@dataclass(frozen=True, slots=True)
class CasesClient:
    """Read operations across case workspaces."""

    context: CrkContext

    def list(self) -> OperationResult:
        """List case slugs under the configured cases root."""
        root = self.context.cases_root or Path("data/cases")
        cases = sorted(entry.name for entry in root.iterdir() if (entry / "case.json").exists()) if root.exists() else []
        return OperationResult.success(
            "cases.list",
            data={"cases": cases},
            counts={"cases": len(cases)},
        )


@dataclass(frozen=True, slots=True)
class CaseRecordsClient:
    """Read operations for one case ledger."""

    context: CrkContext
    case_ref: Path

    @property
    def case_dir(self) -> Path:
        resolved = self.context.resolve_case_ref(self.case_ref)
        if resolved is None:
            raise ValueError("CaseRecordsClient requires a case reference.")
        return resolved

    def list(
        self,
        record_type: str,
        *,
        include_private: bool | None = None,
        limit: int | None = None,
    ) -> OperationResult:
        """Read ledger records with public-safe filtering by default."""
        from adapters.ops import query as query_ops

        raw = query_ops.get_records(
            str(self.case_dir),
            record_type,
            include_private=self._include_private(include_private),
        )
        if raw.ok and limit is not None and len(raw.data.get("records", [])) > limit:
            raw.data["records"] = raw.data["records"][:limit]
            raw.data["truncated"] = True
        return _from_op_result("records.list", raw, case_ref=str(self.case_dir))

    def source_text(
        self,
        source_id: str,
        *,
        include_private: bool | None = None,
        max_chars: int | None = None,
    ) -> OperationResult:
        """Read extracted source text with public-safe filtering by default."""
        from adapters.ops import query as query_ops

        raw = query_ops.get_source_text(
            str(self.case_dir),
            source_id,
            include_private=self._include_private(include_private),
            max_chars=max_chars,
        )
        return _from_op_result("records.source_text", raw, case_ref=str(self.case_dir))

    def _include_private(self, explicit: bool | None) -> bool:
        return self.context.include_private if explicit is None else explicit


def case_info(
    context: CrkContext,
    case_ref: CaseRef,
    *,
    include_private: bool | None = None,
) -> OperationResult:
    """Return case metadata and record counts for one case."""
    from adapters.ops import case as case_ops
    from adapters.ops.safety.policy import filter_public
    from core.casefile import RECORD_FILES, load_records

    path = context.resolve_case_ref(case_ref)
    if path is None:
        return OperationResult.failure("case.info", "Case reference is required.")
    raw = case_ops.case_info(str(path))
    if raw.ok:
        is_internal = context.include_private if include_private is None else include_private
        counts = {}
        for name in RECORD_FILES:
            rows = load_records(path, name)
            counts[name] = len(filter_public(rows, include_private=is_internal))
        raw.data["record_counts"] = counts
        raw.data["include_private"] = is_internal
    return _from_op_result("case.info", raw, case_ref=str(path))


def _from_op_result(operation: str, raw: Any, *, case_ref: str | None = None) -> OperationResult:
    data = dict(getattr(raw, "data", {}) or {})
    return OperationResult(
        ok=bool(getattr(raw, "ok", False)),
        operation=operation,
        case_ref=case_ref,
        data=data,
        errors=[
            {
                "code": _error_code(message),
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


def _error_code(message: str) -> str:
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


__all__ = ["CaseRecordsClient", "CasesClient", "case_info"]
