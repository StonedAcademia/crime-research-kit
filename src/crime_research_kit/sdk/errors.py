"""Public SDK error types and stable error codes."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CrkErrorCode(str, Enum):
    CASE_NOT_FOUND = "case_not_found"
    SOURCE_NOT_FOUND = "source_not_found"
    INVALID_INPUT = "invalid_input"
    VALIDATION_FAILED = "validation_failed"
    PRIVACY_BLOCKED = "privacy_blocked"
    SAFETY_BLOCKED = "safety_blocked"
    NETWORK_FAILED = "network_failed"
    DEPENDENCY_MISSING = "dependency_missing"
    SCHEMA_NOT_FOUND = "schema_not_found"
    OPERATION_FAILED = "operation_failed"


ErrorCode = CrkErrorCode

CASE_NOT_FOUND = CrkErrorCode.CASE_NOT_FOUND.value
SOURCE_NOT_FOUND = CrkErrorCode.SOURCE_NOT_FOUND.value
INVALID_INPUT = CrkErrorCode.INVALID_INPUT.value
VALIDATION_FAILED = CrkErrorCode.VALIDATION_FAILED.value
PRIVACY_BLOCKED = CrkErrorCode.PRIVACY_BLOCKED.value
SAFETY_BLOCKED = CrkErrorCode.SAFETY_BLOCKED.value
NETWORK_FAILED = CrkErrorCode.NETWORK_FAILED.value
DEPENDENCY_MISSING = CrkErrorCode.DEPENDENCY_MISSING.value
SCHEMA_NOT_FOUND = CrkErrorCode.SCHEMA_NOT_FOUND.value
OPERATION_FAILED = CrkErrorCode.OPERATION_FAILED.value


class CrkErrorDetail(BaseModel):
    """Serializable error payload used by SDK operation results."""

    model_config = ConfigDict(extra="allow")

    code: str
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


class CrkError(RuntimeError):
    """SDK exception carrying a stable error code and operation context."""

    default_code = OPERATION_FAILED

    def __init__(
        self,
        message_or_code: str | CrkErrorCode,
        message: str | None = None,
        *,
        code: str | CrkErrorCode | None = None,
        operation: str | None = None,
        case_ref: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if message is None:
            resolved_message = str(message_or_code)
            resolved_code = code or self.default_code
        else:
            resolved_message = message
            resolved_code = code or message_or_code

        self.code = _code_value(resolved_code)
        self.message = resolved_message
        self.operation = operation
        self.case_ref = case_ref
        self.details = dict(details or {})
        super().__init__(self.message)

    def to_detail(self) -> CrkErrorDetail:
        return CrkErrorDetail(
            code=self.code,
            message=self.message,
            operation=self.operation,
            case_ref=self.case_ref,
            details=self.details,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.to_detail().model_dump(mode="json", exclude_none=True)


class CrkInputError(CrkError):
    default_code = INVALID_INPUT


class CrkValidationError(CrkInputError):
    default_code = VALIDATION_FAILED


class CrkSafetyError(CrkError):
    default_code = SAFETY_BLOCKED


class CrkPrivacyError(CrkSafetyError):
    default_code = PRIVACY_BLOCKED


class CrkDependencyError(CrkError):
    default_code = DEPENDENCY_MISSING


class CrkNetworkError(CrkError):
    default_code = NETWORK_FAILED


class CrkNotFoundError(CrkInputError):
    default_code = CASE_NOT_FOUND


InputError = CrkInputError
SafetyError = CrkSafetyError
DependencyError = CrkDependencyError


def _code_value(value: str | CrkErrorCode) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)
