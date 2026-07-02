"""Person-source and fragility facet data products."""

from __future__ import annotations

from typing import Any

from core.casefile import slugify

from adapters.ops.evidence.reports.analysis.classifiers import STATUS_SCORE
from adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from adapters.ops.evidence.reports.common import entity_display, parse_cell_list


def build_person_source_products(ctx: AnalysisContext) -> dict[str, list[dict[str, Any]]]:
    person_source_map: dict[tuple[str, str], set[str]] = {}
    _add_person_entity_sources(ctx, person_source_map)
    _add_person_relationship_sources(ctx, person_source_map)
    _add_person_event_sources(ctx, person_source_map)
    _add_person_event_link_sources(ctx, person_source_map)
    person_source = _person_source_edges(ctx, person_source_map)
    person_source_nodes = _person_source_nodes(ctx, person_source)
    return {"person_source": person_source, "person_source_nodes": person_source_nodes}


def _add_person_entity_sources(ctx: AnalysisContext, person_source_map: dict[tuple[str, str], set[str]]) -> None:
    for person in ctx.people:
        person_id = str(person.get("entity_id", ""))
        for sid in parse_cell_list(person.get("source_ids")):
            person_source_map.setdefault((person_id, sid), set()).add("entity_source")
        for claim_id in parse_cell_list(person.get("claim_ids")):
            claim = ctx.claim_by_id.get(claim_id)
            if claim:
                for sid in parse_cell_list(claim.get("source_ids")):
                    person_source_map.setdefault((person_id, sid), set()).add("entity_claim")


def _add_person_relationship_sources(ctx: AnalysisContext, person_source_map: dict[tuple[str, str], set[str]]) -> None:
    for rel in ctx.relationships:
        for person_id in [str(rel.get("src_entity_id", "")), str(rel.get("dst_entity_id", ""))]:
            if person_id not in ctx.people_by_id:
                continue
            for sid in parse_cell_list(rel.get("source_ids")):
                person_source_map.setdefault((person_id, sid), set()).add("relationship")
            for claim_id in parse_cell_list(rel.get("claim_ids")):
                claim = ctx.claim_by_id.get(claim_id)
                if claim:
                    for sid in parse_cell_list(claim.get("source_ids")):
                        person_source_map.setdefault((person_id, sid), set()).add("relationship_claim")


def _add_person_event_sources(ctx: AnalysisContext, person_source_map: dict[tuple[str, str], set[str]]) -> None:
    for event in ctx.events:
        for person_id in parse_cell_list(event.get("entity_ids")):
            if person_id not in ctx.people_by_id:
                continue
            for sid in parse_cell_list(event.get("source_ids")):
                person_source_map.setdefault((person_id, sid), set()).add("event_entity")
            for claim_id in parse_cell_list(event.get("claim_ids")):
                claim = ctx.claim_by_id.get(claim_id)
                if claim:
                    for sid in parse_cell_list(claim.get("source_ids")):
                        person_source_map.setdefault((person_id, sid), set()).add("event_claim")


def _add_person_event_link_sources(ctx: AnalysisContext, person_source_map: dict[tuple[str, str], set[str]]) -> None:
    for link in ctx.event_links:
        person_id = str(link.get("entity_id", ""))
        if person_id not in ctx.people_by_id:
            continue
        for sid in parse_cell_list(link.get("source_ids")):
            person_source_map.setdefault((person_id, sid), set()).add("event_link")
        for claim_id in parse_cell_list(link.get("claim_ids")):
            claim = ctx.claim_by_id.get(claim_id)
            if claim:
                for sid in parse_cell_list(claim.get("source_ids")):
                    person_source_map.setdefault((person_id, sid), set()).add("event_link_claim")


def _person_source_edges(ctx: AnalysisContext, person_source_map: dict[tuple[str, str], set[str]]) -> list[dict[str, Any]]:
    person_source = []
    for (person_id, sid), contexts in sorted(person_source_map.items(), key=lambda item: (entity_display(ctx.people_by_id.get(item[0][0])), item[0][1])):
        source = ctx.source_by_id.get(sid, {})
        person_source.append({
            "edge_id": f"SP_{slugify(sid, 24).upper()}_{slugify(person_id, 24).upper()}",
            "person_id": person_id,
            "person_name": entity_display(ctx.people_by_id.get(person_id)),
            "cluster_id": ctx.cluster_by_person.get(person_id, ""),
            "source_id": sid,
            "source_title": source.get("title", ""),
            "source_grade": source.get("reliability_grade", ""),
            "source_type": source.get("source_type", ""),
            "publisher": source.get("publisher", ""),
            "contexts": sorted(contexts),
            "public_evidence_state": "public" if ctx.people_by_id.get(person_id, {}).get("public_export", True) is not False and source.get("public_export", True) is not False else "mixed",
            "privacy_flag": ctx.people_by_id.get(person_id, {}).get("public_export", True) is False or source.get("public_export", True) is False,
            "notes": "co-mention/context only" if contexts <= {"event_link", "event_link_claim"} else "",
        })
    return person_source


def _person_source_nodes(ctx: AnalysisContext, person_source: list[dict[str, Any]]) -> list[dict[str, Any]]:
    person_source_nodes: list[dict[str, Any]] = []
    source_node_ids = {row["source_id"] for row in person_source}
    person_node_ids = {row["person_id"] for row in person_source}
    for person_id in sorted(person_node_ids, key=lambda pid: entity_display(ctx.people_by_id.get(pid))):
        person = ctx.people_by_id.get(person_id, {})
        person_source_nodes.append({
            "node_id": f"person:{person_id}",
            "node_type": "person",
            "label": entity_display(person),
            "source_id": "",
            "entity_id": person_id,
            "reliability_grade": "",
            "source_type": "",
            "publisher": "",
            "privacy_level": person.get("privacy_level", ""),
            "living_status": person.get("living_status", ""),
            "role_tags": person.get("role_tags", []),
            "status": person.get("status", ""),
            "public_export": person.get("public_export", True),
            "degree": sum(1 for row in person_source if row["person_id"] == person_id),
        })
    for sid in sorted(source_node_ids):
        source = ctx.source_by_id.get(sid, {})
        person_source_nodes.append({
            "node_id": f"source:{sid}",
            "node_type": "source",
            "label": source.get("title", sid),
            "source_id": sid,
            "entity_id": "",
            "reliability_grade": source.get("reliability_grade", ""),
            "source_type": source.get("source_type", ""),
            "publisher": source.get("publisher", ""),
            "privacy_level": "",
            "living_status": "",
            "role_tags": "",
            "status": "",
            "public_export": source.get("public_export", True),
            "degree": sum(1 for row in person_source if row["source_id"] == sid),
        })
    return person_source_nodes


def build_fragility(edge_load: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    fragility = []
    for row in edge_load.values():
        status = str(row["status"])
        load_score = int(row["load_bearing_score"])
        support_score = STATUS_SCORE.get(status, 0.25)
        if any(cls in {"category_bridge", "lead_context_bridge", "institutional_software_bridge"} for cls in row["bridge_classes"]):
            support_score *= 0.7
        fragility_score = round(max(0.0, min(1.0, 1.0 - support_score + min(0.25, load_score * 0.025))), 3)
        tier = _fragility_tier(fragility_score)
        fragility.append({
            "record_id": row["record_id"],
            "edge_type": row["edge_type"],
            "relation_type": row["relation_type"],
            "relationship_class": ";".join(sorted(row.get("relationship_classes", []))),
            "status": status,
            "load_bearing_score": row["load_bearing_score"],
            "bridge_class": ";".join(sorted(row["bridge_classes"])),
            "source_ids": sorted(row["source_ids"]),
            "claim_ids": sorted(row["claim_ids"]),
            "support_score": round(support_score, 3),
            "fragility_score": fragility_score,
            "fragility_tier": tier,
            "required_caveat": "Do not narrate as direct influence/contact." if tier in {"fragile", "lead_only"} else "",
            "example_path": row["example_path"],
        })
    fragility.sort(key=lambda row: (-int(row["load_bearing_score"]), str(row["record_id"])))
    return fragility


def _fragility_tier(fragility_score: float) -> str:
    if fragility_score <= 0.25:
        return "stable"
    if fragility_score <= 0.5:
        return "qualified"
    if fragility_score <= 0.75:
        return "fragile"
    return "lead_only"
