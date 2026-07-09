"""Deterministic hub and structural-cluster rules for visual exports."""

from __future__ import annotations

import re
from typing import Any

from crime_research_kit._runtime.adapters.ops.evidence.reports.common import parse_cell_list

SUBPROJECT_RE = re.compile(r"\bSUB(?:PROJECT|PROJ)?[_\s-]*(\d{1,3})|\bSubproject\s+(\d{1,3})", re.I)

CLUSTER_LABELS = {
    "PROGRAM_CONTEXT": "Program and agency context",
    "DOCUMENT_CONTEXT": "Omnibus document and hearing context",
    "EVENT_CONTEXT": "Other dated events",
    "ENTITY_CONTEXT": "Other entities",
}

SEMANTIC_FACETS = [
    ("activity_field_testing", ("safehouse", "safe house", "midnight climax", "unwitting", "field test")),
    ("activity_academic_front", ("human ecology", "university", "college", "foundation", "grant", "gorman", "academic")),
    ("activity_drug_chemical_bio", ("lsd", "drug", "chemical", "toxin", "biological", "bw/cw", "staphylococcus", "material")),
    ("activity_behavioral", ("hypnosis", "psychic driving", "depattern", "behavior", "interrogation", "sensory", "sleep")),
    ("activity_tech_remote", ("sensor", "radio", "remote", "electromagnetic", "detection", "microwave")),
    ("activity_admin_accounting", ("approval", "obligation", "advance", "invoice", "accounting", "budget", "liquidation")),
]


def subproject_number(*values: Any) -> int | None:
    numbers = subproject_numbers(*values)
    return numbers[0] if numbers else None


def subproject_numbers(*values: Any) -> list[int]:
    text = " ".join(str(value or "") for value in values)
    seen: set[int] = set()
    numbers: list[int] = []
    for match in SUBPROJECT_RE.finditer(text):
        number = int(match.group(1) or match.group(2))
        if number not in seen:
            seen.add(number)
            numbers.append(number)
    return numbers


def cluster_for(layer: str, *values: Any) -> tuple[str, str]:
    text = " ".join(str(value or "") for value in values).lower()
    number = subproject_number(*values)
    if number is not None:
        start = ((number - 1) // 20) * 20 + 1
        end = start + 19
        cluster_id = f"SP_{start:03d}_{end:03d}"
        return cluster_id, f"Subprojects {start:03d}-{end:03d}"
    if any(token in text for token in ["senate", "hearing", "report", "briefing book", "reading room", "inspector general"]):
        return "DOCUMENT_CONTEXT", CLUSTER_LABELS["DOCUMENT_CONTEXT"]
    if any(token in text for token in ["mkultra", "mk-ultra", "mksearch", "mkdelta", "mknaomi", "cia", "technical services"]):
        return "PROGRAM_CONTEXT", CLUSTER_LABELS["PROGRAM_CONTEXT"]
    if layer == "event":
        return "EVENT_CONTEXT", CLUSTER_LABELS["EVENT_CONTEXT"]
    return "ENTITY_CONTEXT", CLUSTER_LABELS["ENTITY_CONTEXT"]


def semantic_facets(*values: Any) -> list[str]:
    text = " ".join(str(value or "") for value in values).lower()
    return [facet for facet, keywords in SEMANTIC_FACETS if any(keyword in text for keyword in keywords)]


def hub_role(row: dict[str, Any], degree_threshold: int) -> str:
    node_id = str(row.get("node_id", ""))
    label = str(row.get("label", ""))
    text = f"{node_id} {label}".lower()
    degree = _int(row.get("degree"))
    if node_id in {"E_MKULTRA", "E_CIA", "E_TSD"} or "project mkultra" == label.lower():
        return "program_hub" if "mkultra" in text else "agency_hub"
    if "technical services division" in text:
        return "division_hub"
    if subproject_number(node_id, label) is None and any(token in text for token in ["senate", "hearing", "briefing book", "inspector general report"]):
        return "omnibus_source_context"
    if subproject_number(node_id, label) is None and degree >= degree_threshold:
        return "high_degree_context"
    return ""


def facet_types(edge: dict[str, Any]) -> str:
    fields = ["relation_type", "relationship_class", "relation_family", "bridge_class", "src_label", "dst_label", "notes"]
    raw_text = " ".join(str(edge.get(field, "")) for field in fields)
    text = raw_text.lower()
    facets: list[str] = []
    for facet, tokens in [
        ("funding", ("fund", "grant", "allot", "obligation", "budget", "advance", "invoice", "reimburse")),
        ("institution_location", ("university", "college", "institute", "hospital", "location", "safehouse", "safe house", "annex", "site")),
        ("document_subject", ("subproject_of", "document", "source", "report", "hearing", "subject")),
        ("continuation_transfer", ("successor", "component", "continuation", "renewal", "transfer", "replacement")),
        ("personnel_role", ("personnel", "chief", "role", "researcher", "principal", "monitor", "administered")),
        ("contradiction_caveat", ("contested", "disputed", "boundary", "caveat", "hypothesis", "unverified")),
    ]:
        if any(token in text for token in tokens):
            facets.append(facet)
    facets.extend(semantic_facets(raw_text))
    return ";".join(facets or ["context"])


def edge_weight(edge: dict[str, Any], src_hub: bool, dst_hub: bool) -> float:
    weight = _float(edge.get("evidence_weight"), 0.35)
    text = " ".join(str(edge.get(field, "")) for field in ["relation_type", "relationship_class", "relation_family", "bridge_class"]).lower()
    if "subproject_of" in text:
        weight *= 0.22
    if "co_mention" in text or "event_context" in text:
        weight *= 0.28
    if src_hub or dst_hub:
        weight *= 0.35
    facets = set(parse_cell_list(facet_types(edge)))
    if facets & {"funding", "institution_location", "continuation_transfer", "personnel_role"}:
        weight *= 1.35
    if "contradiction_caveat" in facets:
        weight *= 0.55
    return round(max(0.03, min(weight, 2.5)), 3)


def edge_visibility(edge: dict[str, Any], weight: float, src_hub: bool, dst_hub: bool) -> str:
    if edge.get("public_export", True) is False:
        return "internal"
    text = " ".join(str(edge.get(field, "")) for field in ["relation_type", "relationship_class", "relation_family"]).lower()
    if src_hub or dst_hub:
        return "context"
    if weight < 0.18 or "co_mention" in text:
        return "hidden_by_default"
    return "default"


def join(values: Any) -> str:
    return ";".join(sorted(set(parse_cell_list(values))))


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0
