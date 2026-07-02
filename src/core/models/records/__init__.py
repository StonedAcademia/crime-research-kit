"""Pydantic models mirroring the canonical record schemas in docs/schemas/."""

from __future__ import annotations

from pydantic import BaseModel

from .case import ArtifactRecord, EntityRecord, PlaceRecord, SourceRecord
from .evidence import ClaimRecord, EventLinkRecord, EventRecord, RelationshipRecord
from .review import QuoteRecord, RedactionRecord, ResearchActionRecord, SourceSpanRecord

MODEL_BY_RECORD: dict[str, type[BaseModel]] = {
    "sources": SourceRecord,
    "entities": EntityRecord,
    "places": PlaceRecord,
    "artifacts": ArtifactRecord,
    "claims": ClaimRecord,
    "events": EventRecord,
    "event_links": EventLinkRecord,
    "relationships": RelationshipRecord,
    "source_spans": SourceSpanRecord,
    "quotes": QuoteRecord,
    "research_actions": ResearchActionRecord,
    "redactions": RedactionRecord,
}

__all__ = ["MODEL_BY_RECORD", *(model.__name__ for model in MODEL_BY_RECORD.values())]
