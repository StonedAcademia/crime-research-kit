"""Typed models for evidence records: claims, events, event links, relationships."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

EvidenceStatus = Literal["verified", "corroborated", "single_source", "disputed", "unverified", "excluded"]
RelationshipClass = Literal[
    "documented_successor", "method_diffusion", "personnel_bridge",
    "narrative_inheritance", "contested_overlap", "hypothesis_requires_more_sources",
]


class ClaimRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    claim_id: str
    claim: str
    status: Literal[
        "verified", "corroborated", "single_source", "disputed", "unverified",
        "false_or_retracted", "excluded_from_public_script",
    ]
    confidence: float
    source_ids: list[str]
    claim_type: Literal[
        "identity", "timeline", "relationship", "event", "location", "motive",
        "quote", "background", "legal", "eyewitness", "other",
    ] | None = None
    assertion_type: Literal[
        "source_stated_fact", "allegation", "denial", "court_finding",
        "self_report", "biography_claim", "lead_only", "expert_context",
    ] | None = None
    source_span_ids: list[str] | None = None
    contradicts: list[str] | None = None
    supports: list[str] | None = None
    privacy_review: Literal["clear", "needs_review", "redact", "exclude"] | None = None
    public_export: bool | None = None
    notes: str | None = None


class EventRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str
    title: str
    event_type: str
    source_ids: list[str]
    start_date: str | None = None
    end_date: str | None = None
    date_precision: Literal["exact", "day", "month", "year", "decade", "approximate", "unknown"] | None = None
    place_ids: list[str] | None = None
    entity_ids: list[str] | None = None
    artifact_ids: list[str] | None = None
    claim_ids: list[str] | None = None
    source_span_ids: list[str] | None = None
    confidence: float | None = None
    status: EvidenceStatus | None = None
    public_export: bool | None = None
    notes: str | None = None


class EventLinkRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_link_id: str
    entity_id: str
    event_id: str
    relation_type: str
    source_ids: list[str]
    relationship_class: RelationshipClass | None = None
    basis: str | None = None
    claim_ids: list[str] | None = None
    source_span_ids: list[str] | None = None
    confidence: float | None = None
    status: EvidenceStatus | None = None
    public_export: bool | None = None
    notes: str | None = None


class RelationshipRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    rel_id: str
    src_entity_id: str
    dst_entity_id: str
    relation_type: str
    source_ids: list[str]
    relationship_class: RelationshipClass | None = None
    start_date: str | None = None
    end_date: str | None = None
    claim_ids: list[str] | None = None
    source_span_ids: list[str] | None = None
    confidence: float | None = None
    status: EvidenceStatus | None = None
    public_export: bool | None = None
    notes: str | None = None
