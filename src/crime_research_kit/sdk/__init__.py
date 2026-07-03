"""Public SDK surface for Crime Research Kit."""

from __future__ import annotations

from .cases import CaseRecordsClient, CasesClient
from .client import CaseClient, CrkClient
from .context import CrkContext, TransportMode
from .exports import CaseExportsClient, ExportsClient
from .extractions import CaseExtractionsClient
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
from .review import CaseReviewClient
from .results import OperationResult, OperationWarning
from .sources import CaseSourcesClient

__all__ = [
    "CASE_NOT_FOUND",
    "CaseClient",
    "CaseExtractionsClient",
    "CaseExportsClient",
    "CaseRecordsClient",
    "CaseReviewClient",
    "CaseSourcesClient",
    "CasesClient",
    "CrkContext",
    "CrkClient",
    "CrkDependencyError",
    "CrkError",
    "CrkErrorCode",
    "CrkErrorDetail",
    "ExportsClient",
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
    "TransportMode",
    "VALIDATION_FAILED",
    "get_operation",
    "list_operations",
    "operations_by_domain",
]
