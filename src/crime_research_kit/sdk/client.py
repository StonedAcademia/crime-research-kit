"""Public SDK client entrypoints."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from os import PathLike
from pathlib import Path

from .cases import CaseRecordsClient, CasesClient, case_info
from .context import CrkContext
from .operations import OperationSpec, get_operation, operations_by_domain
from .results import OperationResult
from .sources import CaseSourcesClient

CaseRef = str | PathLike[str] | Path


@dataclass(frozen=True, slots=True)
class CaseClient:
    """Case-scoped SDK handle."""

    context: CrkContext
    case_ref: Path

    @property
    def case_dir(self) -> Path:
        """Resolved case directory for this handle."""
        resolved = self.context.resolve_case_ref(self.case_ref)
        if resolved is None:
            raise ValueError("CaseClient requires a case reference.")
        return resolved

    def operation(self, name: str) -> OperationSpec:
        """Return operation metadata for this case handle."""
        return get_operation(name)

    def operations(self, domain: str) -> tuple[OperationSpec, ...]:
        """Return operation metadata for one SDK domain."""
        return operations_by_domain(domain)

    @property
    def records(self) -> CaseRecordsClient:
        """Record read operations for this case."""
        return CaseRecordsClient(context=self.context, case_ref=self.case_ref)

    @property
    def sources(self) -> CaseSourcesClient:
        """Source intake operations for this case."""
        return CaseSourcesClient(context=self.context, case_ref=self.case_ref)

    def info(self, *, include_private: bool | None = None) -> OperationResult:
        """Return case metadata and public-safe record counts by default."""
        return case_info(self.context, self.case_ref, include_private=include_private)

    def with_privacy(self, *, include_private: bool) -> "CaseClient":
        """Return a copy with a different privacy default."""
        return replace(self, context=self.context.with_privacy(include_private=include_private))


@dataclass(frozen=True, slots=True)
class CrkClient:
    """Top-level SDK client."""

    context: CrkContext = field(default_factory=CrkContext)

    @property
    def cases(self) -> CasesClient:
        """Case workspace read operations."""
        return CasesClient(context=self.context)

    def case(self, case_ref: CaseRef) -> CaseClient:
        """Return a case-scoped client so callers stop passing case_dir."""
        path = case_ref if isinstance(case_ref, Path) else Path(case_ref)
        return CaseClient(context=self.context.with_case_dir(path), case_ref=path)

    def operation(self, name: str) -> OperationSpec:
        """Return operation metadata by public SDK operation name."""
        return get_operation(name)

    def operations(self, domain: str) -> tuple[OperationSpec, ...]:
        """Return operation metadata for one SDK domain."""
        return operations_by_domain(domain)

    def with_context(self, context: CrkContext) -> "CrkClient":
        """Return a copy with a different context."""
        return replace(self, context=context)


__all__ = ["CaseClient", "CaseRef", "CrkClient"]
