"""Shared helpers for evidence report and chart commands."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

SUBCASE_TITLES = {
    "recovery_daytop": "Recovery movement / therapeutic community lineage",
    "parsons_crowley_oto": "Parsons / Crowley / O.T.O.",
    "elan_tti": "Troubled Teen Industry / Elan School",
    "mkultra_cia": "MKULTRA industry / intelligence behavioral research",
    "psi_remote_viewing_gateway": "Psi / remote-viewing / Gateway intelligence lane",
    "pandora_bizarre_ti": "PANDORA / BIZARRE / targeted-individual allegation lane",
    "phoenix_narratives": "Phoenix narrative lane",
    "military_abductions": "Military abduction / super-soldier narrative lane",
    "abuse_interference_allegations": "Abuse-interference allegation lane",
    "software_corporate_intelligence": "Software / corporate-intelligence vector lane",
    "maxwell_barr_epstein": "Epstein industry / Maxwell / Barr / Dalton lane",
    "scientology": "Scientology institutional lane",
    "general": "General / unassigned",
}

RELATIONSHIP_CLASS_TITLES = {
    "documented_successor": "Documented succession / component lineage",
    "method_diffusion": "Method diffusion / institutional borrowing",
    "personnel_bridge": "Personnel / role / affiliation bridge",
    "narrative_inheritance": "Narrative inheritance / story-world growth",
    "contested_overlap": "Contested overlap / disputed institutional tie",
    "hypothesis_requires_more_sources": "Hypothesis requiring more sources",
    "unclassified": "Unclassified (no pack or rule matched)",
}

LEGACY_EXPORT_DIRS = frozenset(
    {
        "analysis_charts",
        "charts",
        "charts_public",
        "charts_internal",
        "timeline",
        "visuals",
        "manim",
    }
)


def reject_legacy_export_dir(path: Path) -> None:
    """Block writes into retired siblings of exports/internal."""
    parts = path.resolve().parts
    for index, part in enumerate(parts[:-1]):
        if part != "exports":
            continue
        next_part = parts[index + 1]
        if next_part in LEGACY_EXPORT_DIRS:
            raise SystemExit(
                f"Retired export directory refused: {path}. "
                "Use exports/internal/visuals or exports/internal/timeline."
            )


def entity_display(entity: dict[str, Any] | None, fallback: str = "") -> str:
    if not entity:
        return fallback
    return str(entity.get("display_name") or entity.get("name") or fallback)


def parse_cell_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [part for part in str(value).split(";") if part]


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"Missing CSV: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def infer_subcase(event: dict[str, Any], claims: list[dict[str, Any]]) -> str:
    text = " ".join([str(event.get("event_id", "")), str(event.get("title", "")), str(event.get("event_type", "")), str(event.get("notes", "")), " ".join(str(claim.get("claim", "")) for claim in claims)]).lower()

    def has(pattern: str) -> bool:
        return re.search(pattern, text) is not None

    if any(has(pattern) for pattern in [r"\bbabalon\b", r"\bparsons\b", r"\bcrowley\b", r"\bo\.t\.o\b", r"\boto\b", r"\bagape lodge\b"]):
        return "parsons_crowley_oto"
    if any(has(pattern) for pattern in [r"\belan\b", r"\btroubled teen\b", r"\bresidential treatment\b", r"\binstitutional child abuse\b", r"\bgao\b", r"\bsica\b"]):
        return "elan_tti"
    if any(has(pattern) for pattern in [r"\bcasolaro\b", r"\bpergamon\b"]):
        return "software_corporate_intelligence"
    if any(has(pattern) for pattern in [r"\bscanate\b", r"\bgondola wish\b", r"\bgrill flame\b", r"\bcenter lane\b", r"\bsun streak\b", r"\bstar gate\b", r"\bstargate\b", r"\bgateway process\b", r"\bmonroe institute\b", r"\bremote viewing\b"]):
        return "psi_remote_viewing_gateway"
    if any(has(pattern) for pattern in [r"\bpandora\b", r"\bbizarre\b", r"\bmoscow signal\b", r"\bsynthetic telepathy\b", r"\bvoice[- ]?to[- ]?skull\b", r"\btargeted individual\b", r"\bgangstalking\b", r"\bdirected energy\b"]):
        return "pandora_bizarre_ti"
    if any(has(pattern) for pattern in [r"\bphoenix project\b", r"\bcamp hero\b", r"\btrauma[- ]based mind control\b"]):
        return "phoenix_narratives"
    if any(has(pattern) for pattern in [r"\bmilitary abduction\b", r"\bsuper[- ]?soldier\b", r"\bsecret space\b"]):
        return "military_abductions"
    if any(has(pattern) for pattern in [r"\bpeoples temple\b"]):
        return "abuse_interference_allegations"
    if any(has(pattern) for pattern in [r"\bmkultra\b", r"\bmk-ultra\b", r"\bmksearch\b", r"\bmkoften\b", r"\bmkchickwit\b", r"\bmknaomi\b", r"\bmkdelta\b", r"\bqkhilltop\b", r"\bhuman ecology\b", r"\ballan memorial\b", r"\bewen cameron\b", r"\bpsychic driving\b", r"\bdepatterning\b", r"\bsubproject 68\b", r"\bcia\b", r"\bdulles\b"]):
        return "mkultra_cia"
    if any(has(pattern) for pattern in [r"\bepstein\b", r"\bghislaine\b", r"\brobert maxwell\b", r"\bdonald barr\b", r"\bdalton\b", r"\bpergamon\b"]):
        return "maxwell_barr_epstein"
    if any(has(pattern) for pattern in [r"\bscientology\b", r"\bdianetics\b"]):
        return "scientology"
    if any(has(pattern) for pattern in [r"\balcoholics anonymous\b", r"\ba\.a\.", r"\baa\b", r"\bdaytop\b", r"\bday top\b", r"\btherapeutic communit"]):
        return "recovery_daytop"
    return "general"


def best_pair_relation(left_roles: list[str], right_roles: list[str]) -> str:
    role_set = set(left_roles + right_roles)
    if left_roles and right_roles and set(left_roles) == {"participant"} and set(right_roles) == {"participant"}:
        return "shared_event_participants"
    if "opened_school" in role_set:
        return "co_opened_school"
    if "founder_mentioned" in role_set:
        return "same_source_founder_context"
    if "contextual_reference" in role_set:
        return "contextual_reference_same_event"
    return "shared_event"


def merge_people_edge(
    edge_map: dict[tuple[str, str], dict[str, Any]],
    src_id: str,
    dst_id: str,
    *,
    people_by_id: dict[str, dict[str, Any]],
    connection_type: str,
    event_ids: list[str] | None = None,
    rel_ids: list[str] | None = None,
    claim_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
    statuses: list[str] | None = None,
    confidence: float | int | str | None = None,
    public_export: bool = True,
    notes: list[str] | None = None,
) -> None:
    if src_id == dst_id:
        return
    left, right = sorted([src_id, dst_id])
    key = (left, right)
    if key not in edge_map:
        edge_map[key] = {"src_entity_id": left, "dst_entity_id": right, "src_name": entity_display(people_by_id.get(left), left), "dst_name": entity_display(people_by_id.get(right), right), "connection_types": [], "event_ids": [], "rel_ids": [], "claim_ids": [], "source_ids": [], "statuses": [], "confidence": 0.0, "public_export": True, "notes": []}
    edge = edge_map[key]
    for field, values in [("connection_types", [connection_type]), ("event_ids", event_ids or []), ("rel_ids", rel_ids or []), ("claim_ids", claim_ids or []), ("source_ids", source_ids or []), ("statuses", statuses or []), ("notes", notes or [])]:
        for value in values:
            if value not in edge[field]:
                edge[field].append(value)
    try:
        edge["confidence"] = max(float(edge.get("confidence", 0.0)), float(confidence or 0.0))
    except (TypeError, ValueError):
        pass
    edge["public_export"] = bool(edge.get("public_export", True) and public_export)


def truncate_label(value: str, limit: int = 42) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def people_graph_groups(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> tuple[dict[str, str], list[list[dict[str, Any]]]]:
    node_ids = [str(node.get("entity_id", "")) for node in nodes]
    parent = {node_id: node_id for node_id in node_ids}

    def find(node_id: str) -> str:
        while parent[node_id] != node_id:
            parent[node_id] = parent[parent[node_id]]
            node_id = parent[node_id]
        return node_id

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for edge in edges:
        src = str(edge.get("src_entity_id", ""))
        dst = str(edge.get("dst_entity_id", ""))
        if src in parent and dst in parent:
            union(src, dst)
    node_by_id = {str(node.get("entity_id", "")): node for node in nodes}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for node_id, node in node_by_id.items():
        grouped.setdefault(find(node_id), []).append(node)
    groups = sorted((sorted(group, key=entity_display) for group in grouped.values()), key=lambda group: (-len(group), entity_display(group[0]) if group else ""))
    group_by_id: dict[str, str] = {}
    for idx, group in enumerate(groups, start=1):
        group_id = f"G{idx}"
        for node in group:
            group_by_id[str(node.get("entity_id", ""))] = group_id
    return group_by_id, groups


def edge_is_lead_only(edge: dict[str, Any]) -> bool:
    connection_types = parse_cell_list(edge.get("connection_types"))
    statuses = parse_cell_list(edge.get("statuses"))
    substantive_types = {"associated_with", "co_opened_school", "co_participant_in_event", "father_of", "founded", "founder_of", "headmaster_of", "official_source_describes_abuse_scheme_with", "opened", "shared_event", "shared_event_participants", "taught_at"}
    evidence_statuses = {"verified", "corroborated", "single_source"}
    if any(kind in substantive_types for kind in connection_types) and any(status in evidence_statuses for status in statuses):
        return False
    if "unverified" in statuses:
        return True
    return any(kind in connection_types for kind in ["co_mentioned_with", "contextual_reference_same_event"])


def edge_evidence_label(edge: dict[str, Any]) -> str:
    statuses = parse_cell_list(edge.get("statuses"))
    connection_types = parse_cell_list(edge.get("connection_types"))
    if "corroborated" in statuses:
        return "corroborated"
    if "single_source" in statuses:
        return "single-source"
    if "unverified" in statuses:
        return "lead-only"
    if any(kind in connection_types for kind in ["co_mentioned_with", "contextual_reference_same_event"]):
        return "context"
    return statuses[0].replace("_", " ") if statuses else "recorded"
