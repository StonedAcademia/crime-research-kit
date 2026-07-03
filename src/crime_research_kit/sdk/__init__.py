"""Public SDK surface for Crime Research Kit."""

from __future__ import annotations

from .context import CrkContext
from .errors import (
    CASE_NOT_FOUND,
    DEPENDENCY_MISSING,
    INVALID_INPUT,
    NETWORK_FAILED,
    OPERATION_FAILED,
    PRIVACY_BLOCKED,
    SAFETY_BLOCKED,
    SCHEMA_NOT_FOUND,
    SOURCE_NOT_FOUND,
    VALIDATION_FAILED,
    CrkDependencyError,
    CrkError,
    CrkErrorCode,
    CrkErrorDetail,
    CrkInputError,
    CrkPrivacyError,
    CrkSafetyError,
    CrkValidationError,
)
from .operations import OPERATION_BY_NAME, OPERATION_SPECS, OperationSpec, SafetyTier, get_operation, list_operations, operations_by_domain
from .results import OperationResult, OperationWarning

__all__ = [
    "CASE_NOT_FOUND",
    "CrkContext",
    "CrkDependencyError",
    "CrkError",
    "CrkErrorCode",
    "CrkErrorDetail",
    "CrkInputError",
    "CrkPrivacyError",
    "CrkSafetyError",
    "CrkValidationError",
    "DEPENDENCY_MISSING",
    "INVALID_INPUT",
    "NETWORK_FAILED",
    "OPERATION_BY_NAME",
    "OPERATION_SPECS",
    "OPERATION_FAILED",
    "OperationResult",
    "OperationSpec",
    "OperationWarning",
    "PRIVACY_BLOCKED",
    "SAFETY_BLOCKED",
    "SCHEMA_NOT_FOUND",
    "SOURCE_NOT_FOUND",
    "SafetyTier",
    "VALIDATION_FAILED",
    "get_operation",
    "list_operations",
    "operations_by_domain",
]
