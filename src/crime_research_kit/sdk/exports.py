"""Public-safe export wrappers for the SDK."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._internal import from_op_result as _from_op_result
from ._internal import operation_name as _op
from ._internal import runner as _runner
from .context import CrkContext
from .results import OperationResult

PUBLIC_NOTE = "public-safe: records with public_export=false were excluded"
PRIVATE_NOTE = "include_private=true: for internal review only, do not publish"


@dataclass(frozen=True, slots=True)
class CaseExportsClient:
    """Public export operations for one case."""

    context: CrkContext
    case_ref: Path

    @property
    def case_dir(self) -> Path:
        resolved = self.context.resolve_case_ref(self.case_ref)
        if resolved is None:
            raise ValueError("CaseExportsClient requires a case reference.")
        return resolved

    def case_visuals(self, *, include_private: bool | None = None, out_dir: str | None = None) -> OperationResult:
        """Plan or run the curated case visual package export."""
        from crime_research_kit._runtime.adapters.ops import exports as export_ops

        is_internal = self._include_private(include_private)
        raw = export_ops.export_case_visuals(
            _runner(self.context),
            str(self.case_dir),
            include_private=is_internal,
            out_dir=out_dir,
        )
        return _result(
            _op("exports.case_visuals"),
            raw,
            case_ref=str(self.case_dir),
            include_private=is_internal,
            outputs=[out_dir or str(self.case_dir / "exports" / "internal" / "visuals")],
        )

    def _include_private(self, explicit: bool | None) -> bool:
        return self.context.include_private if explicit is None else explicit


@dataclass(frozen=True, slots=True)
class ExportsClient:
    """Top-level export operations that are not scoped to one case."""

    context: CrkContext

    def timeline(
        self,
        *,
        cases_root: str | Path | None = None,
        include_private: bool | None = None,
        out_dir: str | None = None,
    ) -> OperationResult:
        """Plan or run the cross-case timeline and corroboration export."""
        from crime_research_kit._runtime.adapters.ops import exports as export_ops

        root = cases_root or self.context.cases_root or Path("data/cases")
        is_internal = self.context.include_private if include_private is None else include_private
        raw = export_ops.export_timeline(_runner(self.context), str(root), include_private=is_internal, out_dir=out_dir)
        return _result(
            _op("exports.timeline"),
            raw,
            include_private=is_internal,
            outputs=[out_dir or str(_default_timeline_dir(Path(root)))],
        )

def _result(
    operation: str,
    raw: Any,
    *,
    case_ref: str | None = None,
    include_private: bool | None = None,
    outputs: list[str] | None = None,
) -> OperationResult:
    result = _from_op_result(operation, raw, case_ref=case_ref)
    updates: dict[str, Any] = {}
    if include_private is not None:
        data = dict(result.data)
        data["privacy"] = {"include_private": include_private, "note": PRIVATE_NOTE if include_private else PUBLIC_NOTE}
        updates["data"] = data
    if outputs and result.ok and not result.outputs:
        updates["outputs"] = outputs
    return result.model_copy(update=updates) if updates else result


def _default_timeline_dir(cases_root: Path) -> Path:
    root = cases_root.expanduser().resolve()
    if (root / "case.json").exists():
        return root / "exports" / "internal" / "timeline"
    return root.parent / "exports" / "internal" / "timeline"


__all__ = ["CaseExportsClient", "ExportsClient"]
