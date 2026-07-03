"""Public SDK result envelope for CRK operations."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .errors import CrkError, CrkErrorDetail, OPERATION_FAILED

ResultRef = str | dict[str, Any]


class OperationWarning(BaseModel):
    """Serializable warning payload for non-fatal operation concerns."""

    model_config = ConfigDict(extra="allow")

    code: str = "warning"
    message: str
    operation: str | None = None
    case_ref: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("code", mode="before")
    @classmethod
    def _normalize_code(cls, value: object) -> str:
        if isinstance(value, Enum):
            return str(value.value)
        return str(value)


class OperationResult(BaseModel):
    """Stable SDK result shape aligned to the Skill API response envelope."""

    model_config = ConfigDict(extra="forbid")

    ok: bool = True
    operation: str
    case_ref: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[CrkErrorDetail] = Field(default_factory=list)
    warnings: list[OperationWarning] = Field(default_factory=list)
    created: list[ResultRef] = Field(default_factory=list)
    updated: list[ResultRef] = Field(default_factory=list)
    outputs: list[ResultRef] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)

    @field_validator("errors", mode="before")
    @classmethod
    def _coerce_errors(cls, value: object) -> list[CrkErrorDetail]:
        if value is None:
            return []
        items = value if isinstance(value, list) else [value]
        return [_error_detail(item) for item in items]

    @field_validator("warnings", mode="before")
    @classmethod
    def _coerce_warnings(cls, value: object) -> list[OperationWarning]:
        if value is None:
            return []
        items = value if isinstance(value, list) else [value]
        return [_warning_detail(item) for item in items]

    @classmethod
    def success(
        cls,
        operation: str,
        *,
        case_ref: str | None = None,
        data: dict[str, Any] | None = None,
        created: list[ResultRef] | None = None,
        updated: list[ResultRef] | None = None,
        outputs: list[ResultRef] | None = None,
        counts: dict[str, int] | None = None,
        warnings: list[OperationWarning | str | dict[str, Any]] | None = None,
        diagnostics: dict[str, Any] | None = None,
    ) -> "OperationResult":
        return cls(
            ok=True,
            operation=operation,
            case_ref=case_ref,
            data=data or {},
            created=created or [],
            updated=updated or [],
            outputs=outputs or [],
            counts=counts or {},
            warnings=warnings or [],
            diagnostics=diagnostics or {},
        )

    @classmethod
    def failure(
        cls,
        operation: str,
        error: CrkError | CrkErrorDetail | str | dict[str, Any],
        *,
        case_ref: str | None = None,
        diagnostics: dict[str, Any] | None = None,
    ) -> "OperationResult":
        return cls(
            ok=False,
            operation=operation,
            case_ref=case_ref,
            errors=[_error_detail(error, operation=operation, case_ref=case_ref)],
            diagnostics=diagnostics or {},
        )

    def to_dict(self, *, include_empty_diagnostics: bool = True) -> dict[str, Any]:
        payload = self.model_dump(mode="json", exclude_none=True)
        if not include_empty_diagnostics and not self.diagnostics:
            payload.pop("diagnostics", None)
        return payload


def _error_detail(
    value: CrkError | CrkErrorDetail | str | dict[str, Any],
    *,
    operation: str | None = None,
    case_ref: str | None = None,
) -> CrkErrorDetail:
    if isinstance(value, CrkError):
        detail = value.to_detail()
    elif isinstance(value, CrkErrorDetail):
        detail = value
    elif isinstance(value, str):
        detail = CrkErrorDetail(code=OPERATION_FAILED, message=value)
    else:
        detail = CrkErrorDetail.model_validate(value)

    if operation and detail.operation is None:
        detail.operation = operation
    if case_ref and detail.case_ref is None:
        detail.case_ref = case_ref
    return detail


def _warning_detail(value: OperationWarning | str | dict[str, Any]) -> OperationWarning:
    if isinstance(value, OperationWarning):
        return value
    if isinstance(value, str):
        return OperationWarning(message=value)
    return OperationWarning.model_validate(value)
