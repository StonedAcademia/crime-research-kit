"""Relationship-family and class classifiers."""

from __future__ import annotations

from typing import Any

from adapters.ops.evidence.reports.common import RELATIONSHIP_CLASS_TITLES


def relation_family(relation_type: str, record_kind: str = "relationship") -> str:
    rel = relation_type.lower()
    if "co_mentioned" in rel:
        return "lead_only_co_mentions"
    if record_kind == "event_link":
        return "event_context"
    if any(term in rel for term in ["found", "co_found", "member", "participant", "opened", "completed_treatment", "program"]):
        return "treatment_lineage"
    if any(term in rel for term in ["father", "family", "sentenced", "criminal", "teacher", "headmaster", "hired"]):
        return "legal_criminal_or_family"
    if any(term in rel for term in ["promis", "inslaw", "cia", "institution", "contract", "inquiry"]):
        return "software_inquiry_context"
    if any(term in rel for term in ["behavior", "authority", "category", "context"]):
        return "category_bridges"
    return "institutional_or_career_roles"


def relationship_class(record: dict[str, Any], record_kind: str = "relationship") -> str:
    explicit = str(record.get("relationship_class") or "").strip()
    if explicit in RELATIONSHIP_CLASS_TITLES:
        return explicit
    relation_type = str(record.get("relation_type", "")).lower()
    status = str(record.get("status", "")).lower()
    notes = str(record.get("notes", "")).lower()
    basis = str(record.get("basis", "")).lower()
    summary = str(record.get("summary", "")).lower()
    record_id = str(record.get("rel_id") or record.get("event_link_id") or record.get("claim_id") or "").lower()
    text = " ".join([record_id, relation_type, status, notes, basis, summary])
    if "co_mentioned" in relation_type:
        return "hypothesis_requires_more_sources"
    if any(term in text for term in ["successor", "part_of_program", "component_of", "absorbed_into", "outgrowth", "redesignated", "program_lineage"]):
        return "documented_successor"
    if any(
        term in text
        for term in [
            "therapeutic_community_model",
            "therapeutic_community",
            "therapeutic-community",
            "source_model_context",
            "model_context",
            "reformulated_program_context",
            "reported_method",
            "treatment_context",
            "treatment-model",
            "treatment model",
            "treatment-method",
            "treatment method",
            "prior_treatment_context",
            "method",
            "behavior_modification",
            "behavior modification",
            "authority_conformity",
            "authority/conformity",
            "obedience research",
            "classic studies in the conformity debate",
            "drug_rehabilitation",
            "drug rehabilitation",
            "rehabilitation program",
            "category_member_context",
            "category bridge",
            "category_bridge",
            "behavioral context",
            "drug rehab category",
            "peer pressure",
            "self-help",
            "residential program",
            "source_describes_as",
            "writings_described_as_basis",
            "based on hubbard",
            "drug residues",
            "narconon",
            "origin_context_for",
        ]
    ):
        return "method_diffusion"
    if any(term in text for term in ["narrative", "legend", "monarch", "montauk", "milab", "super_soldier", "targeted_individual", "synthetic_telepathy", "appears_in_narrative", "alleged_spin_off"]):
        return "narrative_inheritance"
    if status == "disputed" or any(term in text for term in ["contested", "reported_allegation", "allegation", "unclear", "boundary", "house_inquiry", "house question", "question/inquiry", "inquiry lane", "further investigation", "promis", "inslaw", "finders", "jonestown"]):
        return "contested_overlap"
    if status == "unverified" or "lead" in text:
        return "hypothesis_requires_more_sources"
    if record_kind == "event_link":
        return "personnel_bridge"
    if any(term in text for term in ["co_founder", "founder", "member", "participant", "researcher", "affiliated", "classmate", "father", "teacher", "headmaster", "sentenced", "worked", "guided", "approved_project"]):
        return "personnel_bridge"
    return "personnel_bridge"
