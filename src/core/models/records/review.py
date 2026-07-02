"""Typed models for review records: source spans, quotes, research actions, redactions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class SourceSpanRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_span_id: str
    source_id: str
    locator_type: Literal[
        "page", "page_range", "timestamp", "timestamp_range", "line_range",
        "paragraph", "section", "char_range", "byte_range", "url_fragment", "other",
    ]
    locator: Any
    exact_text: str | None = None
    summary: str | None = None
    public_export: bool | None = None
    notes: str | None = None


class QuoteRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    quote_id: str
    source_id: str
    exact_quote: str
    speaker: str | None = None
    page_or_timestamp: str | None = None
    source_span_ids: list[str] | None = None
    supports_claim_ids: list[str] | None = None
    account_type: Literal["firsthand", "secondhand", "unclear", "not_applicable"] | None = None
    public_export: bool | None = None
    notes: str | None = None


class ResearchActionRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    timestamp: str
    action: str
    details: dict[str, Any]
    notes: str | None = None


class RedactionRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    redaction_id: str
    record_id: str
    reason: str
    field: str | None = None
    public_replacement: str | None = None
    source_ids: list[str] | None = None
    notes: str | None = None
