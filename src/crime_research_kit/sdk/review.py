"""Review and audit wrappers for the public SDK."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._internal import from_op_result as _from_op_result
from ._internal import invalid_result as _invalid_result
from ._internal import operation_name as _op
from ._internal import runner as _runner
from .context import CrkContext
from .results import OperationResult

_DEDUPE_RECORD_TYPES = {"all", "entities", "sources", "claims"}


@dataclass(frozen=True, slots=True)
class CaseReviewClient:
    """Review operations for one case."""

    context: CrkContext
    case_ref: Path

    @property
    def case_dir(self) -> Path:
        resolved = self.context.resolve_case_ref(self.case_ref)
        if resolved is None:
            raise ValueError("CaseReviewClient requires a case reference.")
        return resolved

    def validate(self) -> OperationResult:
        """Plan or run case validation."""
        from crime_research_kit._runtime.adapters.ops import case as case_ops

        raw = case_ops.validate(_runner(self.context), str(self.case_dir))
        return _result(_op("review.validate"), raw, case_ref=str(self.case_dir))

    def dedupe(self, *, record_type: str = "all", min_key_chars: int = 12, out: str | None = None) -> OperationResult:
        """Report duplicate candidates without merging or deleting rows."""
        from crime_research_kit._runtime.adapters.ops.evidence import review as review_ops

        operation = _op("review.dedupe")
        if record_type not in _DEDUPE_RECORD_TYPES:
            return _invalid(operation, f"record_type must be one of {sorted(_DEDUPE_RECORD_TYPES)}", str(self.case_dir))
        if min_key_chars < 1:
            return _invalid(operation, "min_key_chars must be greater than zero", str(self.case_dir))
        raw = review_ops.dedupe(
            _runner(self.context),
            str(self.case_dir),
            record_type=record_type,
            min_key_chars=min_key_chars,
            out=out,
        )
        return _result(operation, raw, case_ref=str(self.case_dir))

    def resolve_identities(self, *, min_key_chars: int = 8, include_merged: bool = False, out: str | None = None) -> OperationResult:
        """Report candidate duplicate or ambiguous identities without merging."""
        from crime_research_kit._runtime.adapters.ops.evidence import review as review_ops

        operation = _op("review.resolve_identities")
        if min_key_chars < 1:
            return _invalid(operation, "min_key_chars must be greater than zero", str(self.case_dir))
        raw = review_ops.resolve_identities(
            _runner(self.context),
            str(self.case_dir),
            min_key_chars=min_key_chars,
            include_merged=include_merged,
            out=out,
        )
        return _result(operation, raw, case_ref=str(self.case_dir))

    def audit_contradictions(
        self,
        *,
        include_private: bool | None = None,
        min_overlap: float = 0.45,
        fail_on_flags: bool = False,
        out: str | None = None,
    ) -> OperationResult:
        """Report explicit and likely claim contradictions."""
        from crime_research_kit._runtime.adapters.ops.evidence import review as review_ops

        raw = review_ops.audit_contradictions(
            _runner(self.context),
            str(self.case_dir),
            include_private=self._include_private(include_private),
            min_overlap=min_overlap,
            fail_on_flags=fail_on_flags,
            out=out,
        )
        return _result(_op("review.audit_contradictions"), raw, case_ref=str(self.case_dir))

    def narrative_readiness(
        self,
        *,
        include_private: bool | None = None,
        require_spans: bool = False,
        min_independent_sources: int = 2,
        fail_on_blockers: bool = False,
        out: str | None = None,
    ) -> OperationResult:
        """Report public narrative readiness gaps."""
        from crime_research_kit._runtime.adapters.ops.evidence import review as review_ops

        operation = _op("review.narrative_readiness")
        if min_independent_sources < 1:
            return _invalid(operation, "min_independent_sources must be greater than zero", str(self.case_dir))
        raw = review_ops.review_narrative_readiness(
            _runner(self.context),
            str(self.case_dir),
            include_private=self._include_private(include_private),
            require_spans=require_spans,
            min_independent_sources=min_independent_sources,
            fail_on_blockers=fail_on_blockers,
            out=out,
        )
        return _result(operation, raw, case_ref=str(self.case_dir))

    def audit_privacy_redactions(
        self,
        *,
        include_private: bool | None = None,
        require_redaction_log: bool = False,
        warn_only: bool = False,
        out: str | None = None,
    ) -> OperationResult:
        """Report privacy and redaction issues before public output."""
        from crime_research_kit._runtime.adapters.ops.evidence import review as review_ops

        raw = review_ops.audit_privacy_redactions(
            _runner(self.context),
            str(self.case_dir),
            include_private=self._include_private(include_private),
            require_redaction_log=require_redaction_log,
            warn_only=warn_only,
            out=out,
        )
        return _result(_op("review.audit_privacy_redactions"), raw, case_ref=str(self.case_dir))

    def audit_public_export(self, *, warn_only: bool = False, out: str | None = None) -> OperationResult:
        """Report public export safety issues."""
        from crime_research_kit._runtime.adapters.ops.evidence import review as review_ops

        raw = review_ops.audit_public_export(_runner(self.context), str(self.case_dir), warn_only=warn_only, out=out)
        return _result(_op("review.audit_public_export"), raw, case_ref=str(self.case_dir))

    def audit_source_independence(
        self,
        *,
        include_private: bool | None = None,
        min_title_chars: int = 16,
        fail_on_flags: bool = False,
        out: str | None = None,
    ) -> OperationResult:
        """Report source-chain, wire-copy, and press-release risks."""
        from crime_research_kit._runtime.adapters.ops.evidence import review as review_ops

        operation = _op("review.audit_source_independence")
        if min_title_chars < 1:
            return _invalid(operation, "min_title_chars must be greater than zero", str(self.case_dir))
        raw = review_ops.audit_source_independence(
            _runner(self.context),
            str(self.case_dir),
            include_private=self._include_private(include_private),
            min_title_chars=min_title_chars,
            fail_on_flags=fail_on_flags,
            out=out,
        )
        return _result(operation, raw, case_ref=str(self.case_dir))

    def _include_private(self, explicit: bool | None) -> bool:
        return self.context.include_private if explicit is None else explicit


def _result(operation: str, raw: Any, *, case_ref: str) -> OperationResult:
    return _from_op_result(operation, raw, case_ref=case_ref)


def _invalid(operation: str, message: str, case_ref: str) -> OperationResult:
    return _invalid_result(operation, message, case_ref)


__all__ = ["CaseReviewClient"]
