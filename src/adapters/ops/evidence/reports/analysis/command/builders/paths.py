"""Path atlas data products for analysis chart exports."""

from __future__ import annotations

from typing import Any

from core.casefile import slugify

from adapters.ops.evidence.reports.analysis.classifiers import status_score
from adapters.ops.evidence.reports.analysis.command.context import AnalysisContext
from adapters.ops.evidence.reports.analysis.paths import classify_bridge_path, shortest_analysis_path
from adapters.ops.evidence.reports.analysis.relationships import relationship_class
from adapters.ops.evidence.reports.common import entity_display, parse_cell_list


def build_path_atlas(ctx: AnalysisContext) -> dict[str, list[dict[str, Any]]]:
    path_atlas: list[dict[str, Any]] = []
    path_segments: list[dict[str, Any]] = []
    anchor_id = "E_BILL_W" if "E_BILL_W" in ctx.people_by_id else (
        sorted(ctx.people_by_id, key=lambda eid: entity_display(ctx.people_by_id[eid]))[0]
        if ctx.people_by_id else ""
    )
    if not anchor_id:
        return {"path_atlas": path_atlas, "path_segments": path_segments}
    for person_id, person in sorted(ctx.people_by_id.items(), key=lambda item: entity_display(item[1])):
        if person_id == anchor_id:
            continue
        steps = shortest_analysis_path(ctx.graph, [anchor_id], [person_id])
        if steps is None:
            continue
        statuses = [str(step[2].get("status", "")) for step in steps]
        path_id = f"P_{slugify(entity_display(ctx.people_by_id[anchor_id]), 24).upper()}_{slugify(entity_display(person), 24).upper()}"
        path_atlas.append({
            "path_id": path_id,
            "anchor_person": entity_display(ctx.people_by_id[anchor_id]),
            "target_person": entity_display(person),
            "target_entity_id": person_id,
            "target_cluster": ctx.cluster_by_person.get(person_id, ""),
            "hops": len(steps),
            "over_six_hops": len(steps) > 6,
            "path": ctx.path_label(steps),
            "weakest_status": min(statuses, key=lambda status: status_score(status, packs=ctx.packs)) if statuses else "",
            "bridge_classes": sorted({classify_bridge_path([step], ctx.graph_meta, packs=ctx.packs) for step in steps}),
            "relationship_classes": sorted({
                relationship_class(step[2], str(step[2].get("edge_type", "relationship")), packs=ctx.packs)
                for step in steps
            }),
            "source_ids": sorted({sid for step in steps for sid in parse_cell_list(step[2].get("source_ids"))}),
            "claim_ids": sorted({cid for step in steps for cid in parse_cell_list(step[2].get("claim_ids"))}),
            "caveat": "Contains category/context bridges; path length is not evidence of influence, guilt, membership, or control.",
        })
        for idx, (src, dst, edge) in enumerate(steps, start=1):
            step_class = classify_bridge_path([(src, dst, edge)], ctx.graph_meta, packs=ctx.packs)
            path_segments.append({
                "path_id": path_id,
                "segment_index": idx,
                "src_id": src,
                "src_label": ctx.node_label(src),
                "dst_id": dst,
                "dst_label": ctx.node_label(dst),
                "src_cluster": ctx.graph_meta.get(src, {}).get("cluster_id", ""),
                "dst_cluster": ctx.graph_meta.get(dst, {}).get("cluster_id", ""),
                "record_type": edge.get("edge_type", ""),
                "record_id": edge.get("record_id", ""),
                "relation_type": edge.get("relation_type", ""),
                "relationship_class": edge.get("relationship_class")
                or relationship_class(edge, str(edge.get("edge_type", "relationship")), packs=ctx.packs),
                "segment_status": edge.get("status", ""),
                "segment_confidence": edge.get("confidence", ""),
                "segment_public_export": edge.get("public_export", True),
                "source_ids": parse_cell_list(edge.get("source_ids")),
                "claim_ids": parse_cell_list(edge.get("claim_ids")),
                "is_category_bridge": step_class == "category_bridge",
                "is_context_only": step_class in {"category_bridge", "institutional_software_bridge", "lead_context_bridge", "indirect_context_bridge"},
                "caveat": "context/category/lead edge" if step_class != "direct_or_near_direct" else "",
            })
    return {"path_atlas": path_atlas, "path_segments": path_segments}
