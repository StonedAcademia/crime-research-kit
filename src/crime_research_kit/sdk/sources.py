"""Source intake wrappers for the public SDK."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._internal import exception_result as _exception_result
from ._internal import from_op_result as _from_op_result
from ._internal import invalid_result as _invalid_result
from ._internal import operation_name as _op
from ._internal import runner as _runner
from ._internal import setting as _setting
from .context import CrkContext
from .results import OperationResult

_ADD_METADATA_KEYS = {"reliability_grade", "author", "publisher", "date_published", "archive_url", "notes"}
_INGEST_METADATA_KEYS = {"reliability_grade", "timeout"}


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
        metadata: Mapping[str, Any] | None = None,
        reliability_grade: str | None = None,
        author: str | None = None,
        publisher: str | None = None,
        date_published: str | None = None,
        archive_url: str | None = None,
        notes: str | None = None,
        **extra_metadata: Any,
    ) -> OperationResult:
        """Plan or run manual source registration."""
        from crime_research_kit._runtime.adapters.ops import sources as source_ops

        operation = _op("sources.add")
        case_ref = str(self.case_dir)
        values, error = _source_metadata(
            operation,
            metadata,
            extra_metadata,
            _ADD_METADATA_KEYS,
            case_ref=case_ref,
            reliability_grade=reliability_grade,
            author=author,
            publisher=publisher,
            date_published=date_published,
            archive_url=archive_url,
            notes=notes,
        )
        if error:
            return error
        try:
            raw = source_ops.add_source(
                _runner(self.context),
                case_ref,
                title=title,
                url=url,
                source_type=source_type,
                public_export=public_export,
                **values,
            )
        except Exception as exc:
            return _exception_result(operation, exc, case_ref=case_ref)
        return _from_op_result(operation, raw, case_ref=case_ref)

    def ingest_url(
        self,
        url: str,
        *,
        title: str | None = None,
        source_type: str | None = None,
        public_export: bool = True,
        metadata: Mapping[str, Any] | None = None,
        reliability_grade: str | None = None,
        timeout: int | None = None,
        **extra_metadata: Any,
    ) -> OperationResult:
        """Plan or run URL ingestion for a source."""
        from crime_research_kit._runtime.adapters.ops import sources as source_ops

        operation = _op("sources.ingest_url")
        case_ref = str(self.case_dir)
        values, error = _source_metadata(
            operation,
            metadata,
            extra_metadata,
            _INGEST_METADATA_KEYS,
            case_ref=case_ref,
            reliability_grade=reliability_grade,
            timeout=timeout,
        )
        if error:
            return error
        try:
            raw = source_ops.ingest_url(
                _runner(self.context),
                case_ref,
                url,
                title=title,
                source_type=source_type,
                public_export=public_export,
                **values,
            )
        except Exception as exc:
            return _exception_result(operation, exc, case_ref=case_ref)
        return _from_op_result(operation, raw, case_ref=case_ref)

    def preserve(
        self,
        source_id: str,
        *,
        archive_url: str | None = None,
        content_type: str | None = None,
        out: str | None = None,
    ) -> OperationResult:
        """Plan or run source preservation metadata updates."""
        from crime_research_kit._runtime.adapters.ops import sources as source_ops

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
        from crime_research_kit._runtime.adapters.ops import sources as source_ops

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
        from crime_research_kit._runtime.adapters.ops import sources as source_ops

        try:
            raw = source_ops.parse_source(str(self.case_dir), source_id, force=force)
        except Exception as exc:
            return _exception_result(_op("sources.parse"), exc, case_ref=str(self.case_dir))
        return _from_op_result(_op("sources.parse"), raw, case_ref=str(self.case_dir))

    def ocr(self, source_id: str, *, language: str = "eng", force: bool = False) -> OperationResult:
        """OCR a registered PDF source with optional local tooling."""
        from crime_research_kit._runtime.adapters.ops import sources as source_ops

        try:
            raw = source_ops.ocr_source(str(self.case_dir), source_id, language=language, force=force)
        except Exception as exc:
            return _exception_result(_op("sources.ocr"), exc, case_ref=str(self.case_dir))
        return _from_op_result(_op("sources.ocr"), raw, case_ref=str(self.case_dir))


def _source_metadata(
    operation: str,
    metadata: Mapping[str, Any] | None,
    extra_metadata: Mapping[str, Any],
    supported: set[str],
    *,
    case_ref: str,
    **explicit: Any,
) -> tuple[dict[str, Any], OperationResult | None]:
    if metadata is not None and not isinstance(metadata, Mapping):
        return {}, _invalid_result(operation, "metadata must be a mapping", case_ref)
    values = dict(metadata or {})
    values.update(extra_metadata)
    values.update({key: value for key, value in explicit.items() if value is not None})
    values = {key: value for key, value in values.items() if value is not None}
    unsupported = sorted(set(values) - supported)
    if unsupported:
        return {}, _invalid_result(operation, f"Unsupported source metadata keys: {', '.join(unsupported)}", case_ref)
    error = _validate_metadata_values(operation, values, case_ref)
    return ({}, error) if error else (values, None)


def _validate_metadata_values(operation: str, values: Mapping[str, Any], case_ref: str) -> OperationResult | None:
    for key, value in values.items():
        if key == "timeout":
            if isinstance(value, bool) or not isinstance(value, int):
                return _invalid_result(operation, "metadata.timeout must be an integer", case_ref)
        elif not isinstance(value, str):
            return _invalid_result(operation, f"metadata.{key} must be a string", case_ref)
    return None


__all__ = ["CaseSourcesClient"]
