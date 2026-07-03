"""Name-linking wrappers for the public SDK."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ._internal import from_op_result as _from_op_result
from ._internal import operation_name as _op
from ._internal import runner as _runner
from .context import CrkContext
from .results import OperationResult


@dataclass(frozen=True, slots=True)
class CaseNamesClient:
    """Lead-only name linking operations for one case."""

    context: CrkContext
    case_ref: Path

    @property
    def case_dir(self) -> Path:
        resolved = self.context.resolve_case_ref(self.case_ref)
        if resolved is None:
            raise ValueError("CaseNamesClient requires a case reference.")
        return resolved

    def link(self, *, names: Sequence[str] = (), names_file: str | None = None) -> OperationResult:
        """Plan or run lead-only name linking without guilt inference."""
        from crime_research_kit._runtime.adapters.ops import query as query_ops

        raw = query_ops.link_names(_runner(self.context), str(self.case_dir), names=list(names), names_file=names_file)
        return _from_op_result(_op("names.link"), raw, case_ref=str(self.case_dir))

__all__ = ["CaseNamesClient"]
