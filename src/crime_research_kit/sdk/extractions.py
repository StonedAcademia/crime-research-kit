"""Extraction packet wrappers for the public SDK."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cases import _from_op_result
from .context import CrkContext
from .errors import INVALID_INPUT
from .operations import get_operation
from .results import OperationResult


@dataclass(frozen=True, slots=True)
class CaseExtractionsClient:
    """Extraction packet operations for one case."""

    context: CrkContext
    case_ref: Path

    @property
    def case_dir(self) -> Path:
        resolved = self.context.resolve_case_ref(self.case_ref)
        if resolved is None:
            raise ValueError("CaseExtractionsClient requires a case reference.")
        return resolved

    def draft(self, source_id: str, *, template: str = "generic", excerpt_chars: int = 6000) -> OperationResult:
        """Plan or run a staged extraction packet draft for a source."""
        from adapters.ops import extraction as extraction_ops

        raw = extraction_ops.draft_extraction(
            _runner(self.context),
            str(self.case_dir),
            source_id,
            template=template,
            excerpt_chars=excerpt_chars,
        )
        return _result(_op("extractions.draft"), raw, case_ref=str(self.case_dir))

    def list(self) -> OperationResult:
        """List staged extraction packet filenames."""
        from adapters.ops import extraction as extraction_ops

        raw = extraction_ops.list_packets(str(self.case_dir))
        return _result(_op("extractions.list"), raw, case_ref=str(self.case_dir))

    def read(self, packet_name: str) -> OperationResult:
        """Read one staged extraction packet by bare filename."""
        from adapters.ops import extraction as extraction_ops

        raw = extraction_ops.read_packet(str(self.case_dir), packet_name)
        return _result(_op("extractions.read"), raw, case_ref=str(self.case_dir))

    def save(self, packet_name: str, packet: dict[str, Any]) -> OperationResult:
        """Save a reviewed packet draft under staging/extractions."""
        from adapters.ops import extraction as extraction_ops

        raw = extraction_ops.save_packet(str(self.case_dir), packet_name, packet)
        return _result(_op("extractions.save"), raw, case_ref=str(self.case_dir))

    def import_reviewed(self, packet_name: str, *, approved: bool = False) -> OperationResult:
        """Import a human-reviewed staged packet into canonical records."""
        from adapters.ops import extraction as extraction_ops

        name = _bare_packet_name(packet_name)
        operation = _op("extractions.import_reviewed")
        if name is None:
            return OperationResult.failure(
                operation,
                {"code": INVALID_INPUT, "message": f"Packet must be a bare filename: {packet_name!r}"},
                case_ref=str(self.case_dir),
            )
        packet_path = self.case_dir / "staging" / "extractions" / name
        raw = extraction_ops.import_extraction(
            _runner(self.context),
            str(self.case_dir),
            str(packet_path),
            confirm=approved,
        )
        return _result(operation, raw, case_ref=str(self.case_dir))

    def ner_suggest(self, *, source_id: str | None = None, limit: int = 80) -> OperationResult:
        """Plan or run lead-only named-entity/date suggestions from source text."""
        operation = _op("extractions.ner_suggest")
        if limit < 1:
            return OperationResult.failure(
                operation,
                {"code": INVALID_INPUT, "message": "limit must be greater than zero"},
                case_ref=str(self.case_dir),
            )
        args = ["ner-suggest", str(self.case_dir), "--limit", str(limit)]
        if source_id:
            args.extend(["--source-id", source_id])
        raw = _runner(self.context).run("ner_suggest", args)
        return _result(operation, raw, case_ref=str(self.case_dir))


def _op(name: str) -> str:
    return get_operation(name).name


def _runner(context: CrkContext):
    from adapters.ops.runner import CrkRunner

    return CrkRunner(repo_root=context.repo_root, dry_run=context.dry_run)


def _bare_packet_name(packet_name: str) -> str | None:
    path = Path(packet_name)
    if not packet_name or "/" in packet_name or "\\" in packet_name:
        return None
    if path.is_absolute() or packet_name.startswith(".") or path.name != packet_name:
        return None
    return path.name


def _result(operation: str, raw: Any, *, case_ref: str) -> OperationResult:
    result = _from_op_result(operation, raw, case_ref=case_ref)
    updates: dict[str, Any] = {}
    if isinstance(result.data.get("packets"), list):
        updates["counts"] = {"packets": len(result.data["packets"])}
    if isinstance(result.data.get("path"), str):
        updates["outputs"] = [result.data["path"]]
    return result.model_copy(update=updates) if updates else result


__all__ = ["CaseExtractionsClient"]
