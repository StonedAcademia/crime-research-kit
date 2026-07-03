"""Source intake wrappers for the public SDK."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cases import _from_op_result
from .context import CrkContext
from .errors import DEPENDENCY_MISSING, INVALID_INPUT, NETWORK_FAILED, OPERATION_FAILED, SOURCE_NOT_FOUND
from .operations import get_operation
from .results import OperationResult


@dataclass(frozen=True, slots=True)
class CaseSourcesClient:
    """Source operations for one case."""

    context: CrkContext
    case_ref: Path

    @property
    def case_dir(self) -> Path:
        resolved = self.context.resolve_case_ref(self.case_ref)
        if resolved is None:
            raise ValueError("CaseSourcesClient requires a case reference.")
        return resolved

    def add(
        self,
        *,
        title: str,
        url: str | None = None,
        source_type: str | None = None,
        public_export: bool = True,
        **metadata: Any,
    ) -> OperationResult:
        """Plan or run manual source registration."""
        from adapters.ops import sources as source_ops

        raw = source_ops.add_source(
            _runner(self.context),
            str(self.case_dir),
            title=title,
            url=url,
            source_type=source_type,
            public_export=public_export,
            **metadata,
        )
        return _from_op_result(_op("sources.add"), raw, case_ref=str(self.case_dir))

    def ingest_url(
        self,
        url: str,
        *,
        title: str | None = None,
        source_type: str | None = None,
        public_export: bool = True,
        **metadata: Any,
    ) -> OperationResult:
        """Plan or run URL ingestion for a source."""
        from adapters.ops import sources as source_ops

        raw = source_ops.ingest_url(
            _runner(self.context),
            str(self.case_dir),
            url,
            title=title,
            source_type=source_type,
            public_export=public_export,
            **metadata,
        )
        return _from_op_result(_op("sources.ingest_url"), raw, case_ref=str(self.case_dir))

    def preserve(
        self,
        source_id: str,
        *,
        archive_url: str | None = None,
        content_type: str | None = None,
        out: str | None = None,
    ) -> OperationResult:
        """Plan or run source preservation metadata updates."""
        from adapters.ops import sources as source_ops

        raw = source_ops.preserve_source(
            _runner(self.context),
            str(self.case_dir),
            source_id,
            archive_url=archive_url,
            content_type=content_type,
            out=out,
        )
        return _from_op_result(_op("sources.preserve"), raw, case_ref=str(self.case_dir))

    def discover(self, *, query: str, searxng_url: str | None = None, limit: int = 10, out: str | None = None) -> OperationResult:
        """Search configured SearXNG for lead-only source candidates."""
        from adapters.ops import sources as source_ops

        try:
            raw = source_ops.discover_sources(
                str(self.case_dir),
                query=query,
                searxng_url=searxng_url or _setting(self.context, "searxng_url"),
                limit=limit,
                out=out,
            )
        except Exception as exc:
            return _exception_result(_op("sources.discover"), exc, case_ref=str(self.case_dir))
        return _from_op_result(_op("sources.discover"), raw, case_ref=str(self.case_dir))

    def parse(self, source_id: str, *, force: bool = False) -> OperationResult:
        """Parse a registered source artifact with the optional documents extra."""
        from adapters.ops import sources as source_ops

        try:
            raw = source_ops.parse_source(str(self.case_dir), source_id, force=force)
        except Exception as exc:
            return _exception_result(_op("sources.parse"), exc, case_ref=str(self.case_dir))
        return _from_op_result(_op("sources.parse"), raw, case_ref=str(self.case_dir))

    def ocr(self, source_id: str, *, language: str = "eng", force: bool = False) -> OperationResult:
        """OCR a registered PDF source with optional local tooling."""
        from adapters.ops import sources as source_ops

        try:
            raw = source_ops.ocr_source(str(self.case_dir), source_id, language=language, force=force)
        except Exception as exc:
            return _exception_result(_op("sources.ocr"), exc, case_ref=str(self.case_dir))
        return _from_op_result(_op("sources.ocr"), raw, case_ref=str(self.case_dir))


def _op(name: str) -> str:
    return get_operation(name).name


def _runner(context: CrkContext):
    from adapters.ops.runner import CrkRunner

    return CrkRunner(repo_root=context.repo_root, dry_run=context.dry_run)


def _setting(context: CrkContext, key: str) -> str | None:
    value = context.settings.get(key)
    return str(value) if value else None


def _exception_result(operation: str, exc: Exception, *, case_ref: str) -> OperationResult:
    return OperationResult.failure(
        operation,
        {
            "code": _exception_code(exc),
            "message": str(exc),
            "operation": operation,
            "case_ref": case_ref,
        },
        case_ref=case_ref,
    )


def _exception_code(exc: Exception) -> str:
    message = str(exc)
    lowered = message.lower()
    if isinstance(exc, (ImportError, ModuleNotFoundError, FileNotFoundError)):
        return DEPENDENCY_MISSING
    if "not installed" in lowered or "ocrmypdf" in lowered:
        return DEPENDENCY_MISSING
    if exc.__class__.__module__.startswith("httpx") or "connection" in lowered:
        return NETWORK_FAILED
    if message.startswith("Source not found"):
        return SOURCE_NOT_FOUND
    if "raw_path" in lowered:
        return INVALID_INPUT
    return OPERATION_FAILED


__all__ = ["CaseSourcesClient"]
