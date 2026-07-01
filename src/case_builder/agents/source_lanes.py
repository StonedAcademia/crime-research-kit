"""Source-lane routing policy for the initial case-building agent."""

from __future__ import annotations

from collections.abc import Sequence

from ..models.state import dedupe

FALLBACK_LANES = ["source-capture", "contradiction"]

LANE_TRIGGERS: dict[str, tuple[str, ...]] = {
    "legal-court": ("court", "docket", "filing", "lawsuit", "charge", "hearing", "appeal"),
    "corporate": ("company", "corporation", "nonprofit", "bankruptcy", "board", "officer", "director"),
    "education": ("school", "college", "university", "degree", "alumni", "training"),
    "licensing-professional": ("license", "licensing", "certification", "board", "disciplinary"),
    "media-transcript": ("video", "audio", "podcast", "interview", "transcript", "documentary"),
    "property-location": ("property", "parcel", "deed", "permit", "zoning", "address"),
    "missing-persons": ("missing", "last seen", "last contact", "unidentified", "recovered", "namus", "ncmec"),
    "geographical-location": ("map", "route", "coordinates", "geographic", "geospatial", "sighting", "location"),
    "foia-open-records": ("foia", "open records", "sunshine", "records request"),
    "source-capture": ("archive", "capture", "hash", "preserve", "provenance"),
    "contradiction": ("contradiction", "correction", "retraction", "denial", "disputed", "misidentified"),
}


def infer_source_lanes(subject: str | None, explicit_lanes: Sequence[str] | None = None) -> list[str]:
    """Infer conservative source-planning lanes from the seed subject."""
    if explicit_lanes:
        return dedupe(list(explicit_lanes))
    normalized_subject = (subject or "").lower()
    lanes = [
        lane
        for lane, triggers in LANE_TRIGGERS.items()
        if any(trigger in normalized_subject for trigger in triggers)
    ]
    return dedupe(lanes or FALLBACK_LANES)
