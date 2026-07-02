"""Bridge audit and analysis-path helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.casefile import slugify

from adapters.ops.evidence.reports.analysis.relationships import relationship_class
from adapters.ops.evidence.reports.analysis.vocabulary import VocabPacks, load_default_packs, match_pack
from adapters.ops.evidence.reports.common import entity_display, parse_cell_list, read_csv_dicts


def audit_bridge_class(capacity: str) -> str:
    lowered = capacity.lower()
    if "lead" in lowered:
        return "lead_context_bridge"
    if "drug-rehabilitation" in lowered or "drug rehabilitation" in lowered:
        return "category_only_drug_rehab_bridge"
    if "behavior" in lowered or "authority" in lowered or "category" in lowered:
        return "category_bridge"
    if "software" in lowered or "institutional" in lowered:
        return "institutional_software_bridge"
    if "direct" in lowered:
        return "direct_org_person_context"
    return slugify(capacity or "audit_bridge", 32)


def read_cluster_metadata(clusters_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    cluster_rows: dict[str, dict[str, Any]] = {}
    cluster_labels: dict[str, str] = {}
    summary_path = clusters_dir / "cluster_summary.csv"
    if summary_path.exists():
        for row in read_csv_dicts(summary_path):
            cluster_id = str(row.get("cluster_id") or "")
            if cluster_id:
                cluster_rows[cluster_id] = row
    return cluster_rows, cluster_labels


def parse_cluster_bridge_audit(cdir: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    notes = sorted((cdir / "notes").glob("cluster_bridge_audit*.md"))
    if not notes:
        return {}, []
    text = notes[-1].read_text(encoding="utf-8")
    cluster_labels: dict[str, str] = {}
    bridge_rows: list[dict[str, Any]] = []
    section = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            section = line
            continue
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if section == "## Cluster labels" and len(cells) >= 3 and re.match(r"^C\d+$", cells[0]):
            cluster_labels[cells[0]] = cells[1]
        if section == "## Bridge backbone" and len(cells) >= 6 and "->" in cells[0]:
            src, dst = [part.strip() for part in cells[0].split("->", 1)]
            source_ids = re.findall(r"`([^`]+)`", cells[4])
            bridge_rows.append({"bridge_id": f"B_{src}_{dst}_{slugify(cells[1], 32).upper()}", "src_cluster": src, "dst_cluster": dst, "capacity": cells[1], "audit_path": cells[2], "audit_status": cells[3], "audit_source_ids": source_ids, "boundary_text": cells[5]})
    return cluster_labels, bridge_rows


def analysis_graph(
    entities: list[dict[str, Any]],
    events: list[dict[str, Any]],
    event_links: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    allowed_statuses: set[str] | None = None,
    packs: VocabPacks | None = None,
) -> tuple[dict[str, list[tuple[str, dict[str, Any]]]], dict[str, dict[str, Any]]]:
    allowed = allowed_statuses or {"verified", "corroborated", "single_source"}
    graph: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    meta: dict[str, dict[str, Any]] = {}
    entity_by_id = {str(entity.get("entity_id")): entity for entity in entities}

    def add_node(node_id: str, label: str, layer: str) -> None:
        meta.setdefault(node_id, {"id": node_id, "label": label, "layer": layer})

    def add_edge(left: str, right: str, record: dict[str, Any], record_id: str, edge_type: str) -> None:
        status = str(record.get("status", ""))
        if status not in allowed:
            return
        edge = {
            "record_id": record_id,
            "edge_type": edge_type,
            "relation_type": record.get("relation_type", edge_type),
            "relationship_class": relationship_class(record, edge_type, packs=packs),
            "status": status,
            "source_ids": parse_cell_list(record.get("source_ids")),
            "claim_ids": parse_cell_list(record.get("claim_ids")),
            "confidence": record.get("confidence", ""),
            "notes": record.get("notes", ""),
            "public_export": record.get("public_export", True),
        }
        graph.setdefault(left, []).append((right, edge))
        graph.setdefault(right, []).append((left, edge))

    for entity in entities:
        add_node(str(entity.get("entity_id")), entity_display(entity), str(entity.get("entity_type", "entity")))
    for event in events:
        add_node("EVENT:" + str(event.get("event_id")), str(event.get("title") or event.get("event_id")), "event")
    for rel in relationships:
        src = str(rel.get("src_entity_id", ""))
        dst = str(rel.get("dst_entity_id", ""))
        if src in entity_by_id and dst in entity_by_id:
            add_edge(src, dst, rel, str(rel.get("rel_id", "")), "relationship")
    for link in event_links:
        entity_id = str(link.get("entity_id", ""))
        event_id = "EVENT:" + str(link.get("event_id", ""))
        if entity_id in entity_by_id and event_id in meta:
            add_edge(entity_id, event_id, link, str(link.get("event_link_id", "")), "event_link")
    return graph, meta


def shortest_analysis_path(
    graph: dict[str, list[tuple[str, dict[str, Any]]]],
    starts: list[str],
    goals: list[str],
) -> list[tuple[str, str, dict[str, Any]]] | None:
    goal_set = set(goals)
    queue = list(starts)
    previous: dict[str, tuple[str | None, dict[str, Any] | None]] = {node: (None, None) for node in starts}
    for node in queue:
        if node in goal_set:
            return []
    idx = 0
    while idx < len(queue):
        node = queue[idx]
        idx += 1
        for nxt, edge in graph.get(node, []):
            if nxt in previous:
                continue
            previous[nxt] = (node, edge)
            if nxt in goal_set:
                steps: list[tuple[str, str, dict[str, Any]]] = []
                cur = nxt
                while previous[cur][0] is not None:
                    prev, prev_edge = previous[cur]
                    assert prev is not None and prev_edge is not None
                    steps.append((prev, cur, prev_edge))
                    cur = prev
                return list(reversed(steps))
            queue.append(nxt)
    return None


def classify_bridge_path(
    steps: list[tuple[str, str, dict[str, Any]]],
    meta: dict[str, dict[str, Any]],
    packs: VocabPacks | None = None,
) -> str:
    labels = " ".join(meta.get(node, {}).get("label", node) for step in steps for node in step[:2]).lower()
    notes = " ".join(str(step[2].get("notes", "")) for step in steps).lower()
    classes = {relationship_class(step[2], str(step[2].get("edge_type", "relationship")), packs=packs) for step in steps}
    if "hypothesis_requires_more_sources" in classes:
        return "hypothesis_requires_more_sources_bridge"
    if "contested_overlap" in classes:
        return "contested_overlap_bridge"
    if "narrative_inheritance" in classes:
        return "narrative_inheritance_bridge"
    if "method_diffusion" in classes:
        return "method_diffusion_bridge"
    if "documented_successor" in classes:
        return "documented_successor_bridge"
    label_match = match_pack(labels, (packs or load_default_packs()).bridge_labels)
    if label_match:
        return label_match
    if "lead" in notes or "alleged" in notes:
        return "lead_context_bridge"
    if len(steps) <= 2:
        return "direct_or_near_direct"
    return "indirect_context_bridge"
