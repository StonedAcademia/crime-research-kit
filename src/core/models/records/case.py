"""Typed models for case-scope records: sources, entities, places, artifacts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

SourceType = Literal[
    "news_article", "eyewitness_account", "court_record", "government_record",
    "official_report", "interview", "memoir", "book", "documentary", "academic",
    "archive", "social_media_lead", "other",
]
ReliabilityGrade = Literal["A", "B", "C", "D", "X"]


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_id: str
    title: str
    source_type: SourceType
    reliability_grade: ReliabilityGrade
    date_accessed: str
    author: str | None = None
    publisher: str | None = None
    date_published: str | None = None
    url: str | None = None
    archive_url: str | None = None
    raw_path: str | None = None
    text_path: str | None = None
    content_type: str | None = None
    capture_method: Literal["ingest_url", "manual_registration", "archive_lookup", "local_file", "registered_source"] | None = None
    capture_timestamp: str | None = None
    preservation_checked_at: str | None = None
    raw_sha256: str | None = None
    text_sha256: str | None = None
    raw_size_bytes: int | None = None
    text_size_bytes: int | None = None
    preservation_status: Literal["captured", "registered_with_archive", "metadata_only", "missing_artifacts"] | None = None
    preservation_warnings: list[str] | None = None
    independence_group: str | None = None
    notes: str | None = None
    public_export: bool | None = None


class EntityRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    entity_id: str
    entity_type: Literal[
        "person", "organization", "group", "institution", "publication", "place_alias",
        "object", "vehicle", "document", "recording", "event_series", "other",
    ]
    name: str
    status: Literal["confirmed", "candidate", "excluded", "merged"]
    source_ids: list[str]
    display_name: str | None = None
    aliases: list[str] | None = None
    role_tags: list[str] | None = None
    privacy_level: Literal["public_figure", "limited_purpose_public", "private_person", "minor", "not_applicable", "unknown"] | None = None
    living_status: Literal["living", "deceased", "unknown", "not_applicable"] | None = None
    claim_ids: list[str] | None = None
    public_export: bool | None = None
    notes: str | None = None


class PlaceRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    place_id: str
    name: str
    source_ids: list[str]
    place_type: str | None = None
    admin_area: str | None = None
    country: str | None = None
    lat: float | None = None
    lon: float | None = None
    precision: Literal["exact", "approximate", "city_only", "region_only", "unknown"] | None = None
    privacy_sensitive: bool | None = None
    public_export: bool | None = None
    notes: str | None = None


class ArtifactRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    artifact_id: str
    artifact_type: Literal[
        "document", "letter", "photo", "recording", "vehicle", "object",
        "weapon_public_record", "digital_file", "book", "publication", "other",
    ]
    name: str
    source_ids: list[str]
    description: str | None = None
    source_span_ids: list[str] | None = None
    claim_ids: list[str] | None = None
    sensitivity: Literal["low", "medium", "high", "exclude"] | None = None
    public_export: bool | None = None
    notes: str | None = None
