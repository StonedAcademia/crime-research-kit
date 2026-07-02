#!/usr/bin/env python3
"""True Crime / Cult-Origin Research CLI.

This tool is intentionally simple and local-first. It helps a Codex agent create
case folders, register public sources, stage source extraction, import structured
JSON records, validate JSONL files, and export Manim-ready CSVs.
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

SRC_ROOT = Path(__file__).resolve().parents[4] / "src"
if SRC_ROOT.exists() and str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.casefile import (  # noqa: E402
    CasefileError,
    RECORD_FILES,
    append_jsonl,
    case_path,
    log_action,
    now_utc,
    read_jsonl,
    records_dir,
    record_path,
    resolve_case_path as case_relative_path,
    slugify,
    stable_id,
    today,
    write_json,
    write_jsonl,
)
from adapters.ops.casework.records.workspace import (  # noqa: E402
    add_source,
    find_source,
    init_case,
    load_sources,
)
from adapters.ops.casework.records.extractions import (  # noqa: E402
    EXTRACTION_TEMPLATE_FILES,
    draft_extraction,
    import_extraction,
)
from adapters.ops.casework.records.intake.suggestions import ner_suggest  # noqa: E402
from adapters.ops.casework.records.intake.web import ingest_url  # noqa: E402
from adapters.ops.casework.records.names.command import link_names  # noqa: E402
from adapters.ops.casework.records.names.matching import (  # noqa: E402
    append_if_new,
    build_entity_index,
    clean_id_list,
    co_mention_note,
    contains_name,
    entity_lookup_keys,
    find_entity_for_entry,
    make_candidate_entity,
    pair_ids,
    read_source_texts,
    refresh_entity_from_name_entry,
    source_matches_for_entry,
)
from adapters.ops.casework.records.names.parsing import (  # noqa: E402
    normalize_lookup,
    parse_name_entries,
)
from adapters.ops.casework.records.names.reports.brief import write_name_link_research_brief  # noqa: E402
from adapters.ops.casework.records.planning.open_records import plan_open_records  # noqa: E402
from adapters.ops.casework.records.planning.public_records import (  # noqa: E402
    PUBLIC_RECORD_LANES,
    infer_public_record_lanes,
    plan_public_records,
    public_record_lane_plan,
)
from adapters.ops.casework.records.planning.transcripts import (  # noqa: E402
    SPEAKER_LINE_RE,
    TIMESTAMP_RE,
    index_transcript,
    timestamp_to_seconds,
    transcript_segment_from_line,
)
from adapters.ops.casework.records.validation import validate  # noqa: E402
from adapters.ops.evidence.public_gate import enforce_public_output_gate  # noqa: E402
from adapters.ops.evidence.shared.records import (  # noqa: E402
    compact_record,
    discover_cases,
    flatten,
    normalize_url,
    public_rows,
    record_id,
    report_out_path,
    source_independence_key,
    write_csv,
)
from adapters.ops.evidence.shared.markdown import md_table  # noqa: E402
from adapters.ops.evidence.shared.scoring import date_sort_key, evidence_level, grade_summary  # noqa: E402
from adapters.ops.evidence.quality.preservation import (  # noqa: E402
    preservation_artifact,
    preserve_source,
    source_preservation_report,
)
from adapters.ops.evidence.quality.identity import (  # noqa: E402
    append_identity_candidate,
    entity_resolution_context,
    resolve_identities,
)
from adapters.ops.evidence.quality.contradictions import (  # noqa: E402
    audit_contradictions,
    claim_overlap,
    claim_tokens,
    contradiction_severity,
    make_contradiction_flag,
)
from adapters.ops.evidence.quality.dedupe import append_duplicate_candidate, dedupe  # noqa: E402
from adapters.ops.evidence.quality.safety.privacy import audit_privacy_redactions  # noqa: E402
from adapters.ops.evidence.quality.safety.public_export import audit_public_export  # noqa: E402
from adapters.ops.evidence.quality.safety.readiness import (  # noqa: E402
    review_narrative_readiness,
)
from adapters.ops.evidence.quality.safety.source_independence import source_independence  # noqa: E402
from adapters.ops.evidence.reports.analysis.command.builders.bridges import build_cluster_bridges  # noqa: E402
from adapters.ops.evidence.reports.analysis.command.builders.evidence import build_evidence_products  # noqa: E402
from adapters.ops.evidence.reports.analysis.command.builders.facets.boundary import (  # noqa: E402
    build_boundary_rows,
    build_readiness_products,
)
from adapters.ops.evidence.reports.analysis.command.builders.facets.timelines import build_swimlanes  # noqa: E402
from adapters.ops.evidence.reports.analysis.command.builders.layered import build_layered_graphs  # noqa: E402
from adapters.ops.evidence.reports.analysis.command.builders.paths import build_path_atlas  # noqa: E402
from adapters.ops.evidence.reports.analysis.command.context import load_analysis_context  # noqa: E402
from adapters.ops.evidence.reports.analysis.classifiers import (  # noqa: E402
    GRADE_SCORE,
    STATUS_SCORE,
    best_grade,
    boundary_signal,
    public_ready_record,
    readiness_label,
    record_id_for,
    source_grade_counts,
    source_grade_score,
    weakest_status,
)
from adapters.ops.evidence.reports.analysis.paths import (  # noqa: E402
    analysis_graph,
    audit_bridge_class,
    classify_bridge_path,
    parse_cluster_bridge_audit,
    read_cluster_metadata,
    shortest_analysis_path,
)
from adapters.ops.evidence.reports.analysis.pages.render import (  # noqa: E402
    render_analysis_chart_page,
    render_analysis_dashboard,
)
from adapters.ops.evidence.reports.analysis.pages.specs import build_analysis_chart_specs  # noqa: E402
from adapters.ops.evidence.reports.analysis.relationships import relation_family, relationship_class  # noqa: E402
from adapters.ops.evidence.reports.case_outputs import export_manim, report  # noqa: E402
from adapters.ops.evidence.reports.case_charts.command import export_case_charts  # noqa: E402
from adapters.ops.evidence.reports.clusters.command import export_people_clusters  # noqa: E402
from adapters.ops.evidence.reports.common import (  # noqa: E402
    RELATIONSHIP_CLASS_TITLES,
    entity_display,
    parse_cell_list,
    read_csv_dicts,
    truncate_label,
)
from adapters.ops.evidence.reports.timeline import export_timeline  # noqa: E402
from adapters.ops.evidence.reports.weights import (  # noqa: E402
    evidence_edge_weight,
    parse_float,
)

def export_analysis_charts(args: argparse.Namespace) -> None:
    ctx = load_analysis_context(args)
    cdir = ctx.cdir
    include_private = ctx.include_private
    out = ctx.out
    case_title = ctx.case_title
    sources = ctx.sources
    entities = ctx.entities
    claims = ctx.claims
    events = ctx.events
    event_links = ctx.event_links
    relationships = ctx.relationships
    source_by_id = ctx.source_by_id
    claim_by_id = ctx.claim_by_id
    entity_by_id = ctx.entity_by_id
    people = ctx.people
    people_by_id = ctx.people_by_id
    cluster_by_person = ctx.cluster_by_person
    cluster_summary = ctx.cluster_summary
    cluster_labels = ctx.cluster_labels
    audit_bridges = ctx.audit_bridges
    graph = ctx.graph
    graph_meta = ctx.graph_meta
    cluster_members = ctx.cluster_members
    cluster_ids = ctx.cluster_ids
    bridge_products = build_cluster_bridges(ctx)
    sankey_nodes = bridge_products["sankey_nodes"]
    cluster_bridge_rows = bridge_products["cluster_bridge_rows"]
    cluster_bridge_links = bridge_products["cluster_bridge_links"]
    bridge_segment_rows = bridge_products["bridge_segment_rows"]
    edge_load = bridge_products["edge_load"]
    path_products = build_path_atlas(ctx)
    path_atlas = path_products["path_atlas"]
    path_segments = path_products["path_segments"]

    layered_products = build_layered_graphs(ctx)
    layered_nodes = layered_products["layered_nodes"]
    layered_edges = layered_products["layered_edges"]
    layered_v2_nodes = layered_products["layered_v2_nodes"]
    layered_v2_edges = layered_products["layered_v2_edges"]
    layered_v2_layers = layered_products["layered_v2_layers"]

    evidence_products = build_evidence_products(ctx)
    claim_heatmap = evidence_products["claim_heatmap"]
    claim_matrix = evidence_products["claim_matrix"]
    claim_edge_rows = evidence_products["claim_edge_rows"]
    heatmap_aggregate = evidence_products["heatmap_aggregate"]
    source_dashboard = evidence_products["source_dashboard"]
    source_grade_count_rows = evidence_products["source_grade_count_rows"]

    boundary_rows = build_boundary_rows(ctx)

    swimlanes = build_swimlanes(ctx)

    relation_counts: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for rel in relationships:
        relation_type = str(rel.get("relation_type", ""))
        rel_class = relationship_class(rel)
        status = str(rel.get("status", ""))
        family = relation_family(relation_type)
        public_scope = "public" if rel.get("public_export", True) is not False else "internal"
        key = ("relationship", rel_class, family, relation_type, status + "/" + public_scope)
        bucket = relation_counts.setdefault(key, {
            "record_kind": "relationship",
            "relationship_class": rel_class,
            "relationship_class_label": RELATIONSHIP_CLASS_TITLES.get(rel_class, rel_class),
            "relation_family": family,
            "relation_type": relation_type,
            "status": status,
            "public_scope": public_scope,
            "row_count": 0,
            "weighted_count": 0.0,
            "source_count": 0,
            "claim_count": 0,
            "boundary_count": 0,
            "lead_only_count": 0,
            "sample_record_ids": [],
        })
        bucket["row_count"] += 1
        weight = STATUS_SCORE.get(status, 0.3)
        if "co_mentioned" in relation_type:
            weight *= 0.1
            bucket["lead_only_count"] += 1
        bucket["weighted_count"] = round(float(bucket["weighted_count"]) + weight, 3)
        bucket["source_count"] += len(parse_cell_list(rel.get("source_ids")))
        bucket["claim_count"] += len(parse_cell_list(rel.get("claim_ids")))
        bucket["boundary_count"] += 1 if boundary_signal(rel) else 0
        if len(bucket["sample_record_ids"]) < 8:
            bucket["sample_record_ids"].append(rel.get("rel_id", ""))
    for link in event_links:
        relation_type = str(link.get("relation_type", ""))
        rel_class = relationship_class(link, "event_link")
        status = str(link.get("status", ""))
        family = relation_family(relation_type, "event_link")
        public_scope = "public" if link.get("public_export", True) is not False else "internal"
        key = ("event_link", rel_class, family, relation_type, status + "/" + public_scope)
        bucket = relation_counts.setdefault(key, {
            "record_kind": "event_link",
            "relationship_class": rel_class,
            "relationship_class_label": RELATIONSHIP_CLASS_TITLES.get(rel_class, rel_class),
            "relation_family": family,
            "relation_type": relation_type,
            "status": status,
            "public_scope": public_scope,
            "row_count": 0,
            "weighted_count": 0.0,
            "source_count": 0,
            "claim_count": 0,
            "boundary_count": 0,
            "lead_only_count": 0,
            "sample_record_ids": [],
        })
        bucket["row_count"] += 1
        weight = STATUS_SCORE.get(status, 0.3)
        if "co_mentioned" in relation_type:
            weight *= 0.1
            bucket["lead_only_count"] += 1
        bucket["weighted_count"] = round(float(bucket["weighted_count"]) + weight, 3)
        bucket["source_count"] += len(parse_cell_list(link.get("source_ids")))
        bucket["claim_count"] += len(parse_cell_list(link.get("claim_ids")))
        bucket["boundary_count"] += 1 if boundary_signal(link) else 0
        if len(bucket["sample_record_ids"]) < 8:
            bucket["sample_record_ids"].append(link.get("event_link_id", ""))
    relation_type_counts = [
        row
        for row in sorted(relation_counts.values(), key=lambda item: (-float(item["weighted_count"]), str(item["relation_type"])))
    ]

    person_source_map: dict[tuple[str, str], set[str]] = {}
    for person in people:
        person_id = str(person.get("entity_id", ""))
        for sid in parse_cell_list(person.get("source_ids")):
            person_source_map.setdefault((person_id, sid), set()).add("entity_source")
        for claim_id in parse_cell_list(person.get("claim_ids")):
            claim = claim_by_id.get(claim_id)
            if claim:
                for sid in parse_cell_list(claim.get("source_ids")):
                    person_source_map.setdefault((person_id, sid), set()).add("entity_claim")
    for rel in relationships:
        for person_id in [str(rel.get("src_entity_id", "")), str(rel.get("dst_entity_id", ""))]:
            if person_id in people_by_id:
                for sid in parse_cell_list(rel.get("source_ids")):
                    person_source_map.setdefault((person_id, sid), set()).add("relationship")
                for claim_id in parse_cell_list(rel.get("claim_ids")):
                    claim = claim_by_id.get(claim_id)
                    if claim:
                        for sid in parse_cell_list(claim.get("source_ids")):
                            person_source_map.setdefault((person_id, sid), set()).add("relationship_claim")
    for event in events:
        for person_id in parse_cell_list(event.get("entity_ids")):
            if person_id in people_by_id:
                for sid in parse_cell_list(event.get("source_ids")):
                    person_source_map.setdefault((person_id, sid), set()).add("event_entity")
                for claim_id in parse_cell_list(event.get("claim_ids")):
                    claim = claim_by_id.get(claim_id)
                    if claim:
                        for sid in parse_cell_list(claim.get("source_ids")):
                            person_source_map.setdefault((person_id, sid), set()).add("event_claim")
    for link in event_links:
        person_id = str(link.get("entity_id", ""))
        if person_id in people_by_id:
            for sid in parse_cell_list(link.get("source_ids")):
                person_source_map.setdefault((person_id, sid), set()).add("event_link")
            for claim_id in parse_cell_list(link.get("claim_ids")):
                claim = claim_by_id.get(claim_id)
                if claim:
                    for sid in parse_cell_list(claim.get("source_ids")):
                        person_source_map.setdefault((person_id, sid), set()).add("event_link_claim")
    person_source = []
    for (person_id, sid), contexts in sorted(person_source_map.items(), key=lambda item: (entity_display(people_by_id.get(item[0][0])), item[0][1])):
        source = source_by_id.get(sid, {})
        person_source.append({
            "edge_id": f"SP_{slugify(sid, 24).upper()}_{slugify(person_id, 24).upper()}",
            "person_id": person_id,
            "person_name": entity_display(people_by_id.get(person_id)),
            "cluster_id": cluster_by_person.get(person_id, ""),
            "source_id": sid,
            "source_title": source.get("title", ""),
            "source_grade": source.get("reliability_grade", ""),
            "source_type": source.get("source_type", ""),
            "publisher": source.get("publisher", ""),
            "contexts": sorted(contexts),
            "public_evidence_state": "public" if people_by_id.get(person_id, {}).get("public_export", True) is not False and source.get("public_export", True) is not False else "mixed",
            "privacy_flag": people_by_id.get(person_id, {}).get("public_export", True) is False or source.get("public_export", True) is False,
            "notes": "co-mention/context only" if contexts <= {"event_link", "event_link_claim"} else "",
        })
    person_source_nodes: list[dict[str, Any]] = []
    source_node_ids = {row["source_id"] for row in person_source}
    person_node_ids = {row["person_id"] for row in person_source}
    for person_id in sorted(person_node_ids, key=lambda pid: entity_display(people_by_id.get(pid))):
        person = people_by_id.get(person_id, {})
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
        source = source_by_id.get(sid, {})
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

    readiness_products = build_readiness_products(ctx)
    readiness_rows = readiness_products["readiness_rows"]
    readiness_counts = readiness_products["readiness_counts"]

    fragility = []
    for row in edge_load.values():
        status = str(row["status"])
        load_score = int(row["load_bearing_score"])
        support_score = STATUS_SCORE.get(status, 0.25)
        if any(cls in {"category_bridge", "lead_context_bridge", "institutional_software_bridge"} for cls in row["bridge_classes"]):
            support_score *= 0.7
        fragility_score = round(max(0.0, min(1.0, 1.0 - support_score + min(0.25, load_score * 0.025))), 3)
        if fragility_score <= 0.25:
            tier = "stable"
        elif fragility_score <= 0.5:
            tier = "qualified"
        elif fragility_score <= 0.75:
            tier = "fragile"
        else:
            tier = "lead_only"
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

    write_csv(out / "cluster_bridge_sankey_nodes.csv", sankey_nodes, [
        "cluster_id", "cluster_label", "member_entity_ids", "member_names", "size", "mean_kde_density",
        "internal_edge_weight", "boundary_edge_weight", "notes",
    ])
    write_csv(out / "cluster_bridge_sankey_links.csv", cluster_bridge_links, [
        "bridge_id", "src_cluster", "dst_cluster", "src_cluster_label", "dst_cluster_label", "bridge_class", "relationship_classes", "hops",
        "path", "statuses", "source_ids", "claim_ids", "boundary_claim_ids", "boundary_text", "source_grade_counts",
        "public_readiness", "public_export", "notes",
    ])
    write_csv(out / "cluster_bridge_sankey.csv", cluster_bridge_rows, [
        "bridge_id", "src_cluster", "dst_cluster", "bridge_class", "relationship_classes", "hops", "path", "statuses", "source_ids",
        "claim_ids", "boundary_claim_ids", "boundary_text", "public_readiness", "public_export",
    ])
    write_csv(out / "layered_knowledge_graph_nodes.csv", layered_nodes, [
        "node_id", "label", "layer", "cluster_id", "status", "source_count", "public_export",
    ])
    write_csv(out / "layered_knowledge_graph_edges.csv", layered_edges, [
        "src_id", "dst_id", "src_label", "dst_label", "edge_type", "relation_type", "relationship_class", "status", "confidence", "source_count", "source_ids", "claim_ids", "public_export",
    ])
    write_csv(out / "layered_knowledge_graph_v2_nodes.csv", layered_v2_nodes, [
        "node_id", "label", "layer", "layer_order", "cluster_id", "status", "degree", "source_count",
        "independent_source_count", "best_source_grade", "source_grade_counts", "claim_count", "evidence_state",
        "readiness", "boundary_flag", "public_export", "caveat",
    ])
    write_csv(out / "layered_knowledge_graph_v2_edges.csv", layered_v2_edges, [
        "edge_id", "src_id", "dst_id", "src_label", "dst_label", "src_layer", "dst_layer", "edge_type",
        "relation_type", "relationship_class", "relation_family", "bridge_class", "status", "confidence",
        "evidence_weight", "source_count", "independent_source_count", "best_source_grade", "source_grade_counts",
        "claim_ids", "source_ids", "boundary_claim_ids", "readiness", "boundary_flag", "public_export", "caveat",
    ])
    write_csv(out / "layered_knowledge_graph_v2_layers.csv", layered_v2_layers, [
        "layer", "layer_order", "node_count", "public_node_count", "internal_node_count", "candidate_node_count",
        "source_count", "edge_count", "public_edge_count", "lead_or_disputed_edge_count", "public_ready_edge_count",
        "dominant_statuses", "dominant_relationship_classes",
    ])
    write_csv(out / "evidence_confidence_heatmap.csv", claim_heatmap, [
        "claim_id", "claim", "claim_type", "status", "confidence", "status_score", "source_count", "independent_source_count",
        "best_source_grade", "source_grade_counts", "source_grade_score", "privacy_review", "public_export", "boundary_flag", "readiness",
    ])
    write_csv(out / "evidence_confidence_heatmap_aggregate.csv", heatmap_aggregate, [
        "claim_type", "status", "claim_count", "public_claim_count", "internal_only_count", "needs_review_count",
        "avg_confidence", "avg_source_count", "source_count_total", "a_sources", "b_sources", "c_sources", "d_sources",
        "boundary_claim_count", "claim_ids",
    ])
    write_csv(out / "bridge_fragility.csv", fragility, [
        "record_id", "edge_type", "relation_type", "relationship_class", "status", "load_bearing_score", "bridge_class", "source_ids",
        "claim_ids", "support_score", "fragility_score", "fragility_tier", "required_caveat", "example_path",
    ])
    write_csv(out / "bridge_fragility_segments.csv", bridge_segment_rows, [
        "bridge_id", "segment_index", "src_id", "src_label", "dst_id", "dst_label", "record_type", "record_id",
        "relation_type", "relationship_class", "status", "confidence", "source_ids", "claim_ids", "public_export", "guardrail_note",
    ])
    write_csv(out / "claim_corroboration_matrix.csv", claim_matrix, [
        "claim_id", "claim_label", "source_id", "source_title", "source_grade", "source_type", "source_publisher",
        "claim_status", "claim_confidence", "claim_type", "source_role", "safe_public_cell", "boundary_flag",
        "contradiction_flag", "contradicts", "supports",
    ])
    write_csv(out / "claim_corroboration_edges.csv", claim_edge_rows, [
        "from_claim_id", "to_claim_id", "edge_type", "from_claim_status", "to_claim_status", "from_confidence",
        "to_confidence", "shared_source_count", "from_source_ids", "to_source_ids", "boundary_flag", "safe_public_pair",
    ])
    write_csv(out / "source_quality_dashboard.csv", source_dashboard, [
        "source_id", "title", "reliability_grade", "source_type", "publisher", "date_published", "date_accessed", "url",
        "independence_group", "claim_count", "event_count", "event_link_count", "relationship_count", "entity_count",
        "person_count", "verified_claim_count", "corroborated_claim_count", "single_source_claim_count",
        "disputed_claim_count", "unverified_claim_count", "needs_privacy_review_count", "nonpublic_record_count",
        "source_quality_notes", "public_export",
    ])
    write_csv(out / "sixdof_path_atlas.csv", path_atlas, [
        "path_id", "anchor_person", "target_person", "target_entity_id", "target_cluster", "hops", "over_six_hops",
        "path", "weakest_status", "bridge_classes", "relationship_classes", "source_ids", "claim_ids", "caveat",
    ])
    write_csv(out / "sixdof_path_segments.csv", path_segments, [
        "path_id", "segment_index", "src_id", "src_label", "dst_id", "dst_label", "src_cluster", "dst_cluster",
        "record_type", "record_id", "relation_type", "relationship_class", "segment_status", "segment_confidence", "segment_public_export",
        "source_ids", "claim_ids", "is_category_bridge", "is_context_only", "caveat",
    ])
    write_csv(out / "contradiction_boundary_overlay.csv", boundary_rows, [
        "record_id", "record_type", "status", "claim_type", "boundary_kind", "relationship_class", "summary", "source_ids", "contradicts",
    ])
    write_csv(out / "temporal_cluster_swimlanes.csv", swimlanes, [
        "cluster_id", "cluster_label", "entity_id", "name", "start_date", "end_date", "date_precision", "event_id",
        "event_title", "event_type", "status", "confidence", "event_link_id", "relation_type", "relationship_class", "event_link_status",
        "event_link_confidence", "source_count", "claim_ids", "source_ids", "is_public_safe", "caveat",
    ])
    write_csv(out / "relationship_type_treemap.csv", relation_type_counts, [
        "record_kind", "relationship_class", "relationship_class_label", "relation_family", "relation_type", "status", "public_scope", "row_count", "weighted_count",
        "source_count", "claim_count", "boundary_count", "lead_only_count", "sample_record_ids",
    ])
    write_csv(out / "person_source_bipartite.csv", person_source, [
        "edge_id", "person_id", "person_name", "cluster_id", "source_id", "source_title", "source_grade", "source_type",
        "publisher", "contexts", "public_evidence_state", "privacy_flag", "notes",
    ])
    write_csv(out / "person_source_bipartite_nodes.csv", person_source_nodes, [
        "node_id", "node_type", "label", "source_id", "entity_id", "reliability_grade", "source_type", "publisher",
        "privacy_level", "living_status", "role_tags", "status", "public_export", "degree",
    ])
    write_csv(out / "person_source_bipartite_edges.csv", person_source, [
        "edge_id", "source_id", "person_id", "source_grade", "source_type", "contexts", "public_evidence_state",
        "privacy_flag", "notes",
    ])
    write_csv(out / "public_narrative_readiness.csv", readiness_rows, [
        "record_type", "record_id", "status", "confidence", "source_count", "best_source_grade", "source_grade_counts",
        "public_export", "privacy_review", "readiness", "boundary_flag", "required_caveat", "relationship_class", "summary",
    ])

    chart_data = {
        "sankey_nodes": sankey_nodes,
        "cluster_bridge_links": cluster_bridge_links,
        "cluster_bridges": cluster_bridge_rows,
        "layered_nodes": layered_nodes,
        "layered_edges": layered_edges,
        "layered_v2_nodes": layered_v2_nodes,
        "layered_v2_edges": layered_v2_edges,
        "layered_v2_layers": layered_v2_layers,
        "claim_heatmap": claim_heatmap,
        "heatmap_aggregate": heatmap_aggregate,
        "fragility": fragility,
        "claim_matrix": claim_matrix,
        "source_grade_counts": source_grade_count_rows,
        "source_dashboard": source_dashboard,
        "path_atlas": path_atlas,
        "boundary_rows": boundary_rows,
        "swimlanes": swimlanes,
        "relation_type_counts": relation_type_counts,
        "person_source": person_source,
        "person_source_nodes": person_source_nodes,
        "readiness_counts": readiness_counts,
    }
    chart_specs = build_analysis_chart_specs(chart_data)
    for spec in chart_specs:
        (out / str(spec["filename"])).write_text(
            render_analysis_chart_page(case_title, include_private, spec),
            encoding="utf-8",
        )
    (out / "analysis_charts.html").write_text(
        render_analysis_dashboard(case_title, include_private, chart_specs),
        encoding="utf-8",
    )
    chart_page_lines = [f"- `{spec['filename']}` - {spec['title']}" for spec in chart_specs]
    index = [
        f"# Analysis charts: {case_title}",
        "",
        f"Scope: {'public and private/internal rows' if include_private else 'public-export rows only'}",
        "",
        "## Interactive HTML pages",
        "",
        "- `analysis_charts.html` - chart index",
        *chart_page_lines,
        "",
        "## Files",
        "",
        "- `analysis_charts.html`",
        "- `cluster_bridge_sankey.csv`",
        "- `cluster_bridge_sankey_nodes.csv`",
        "- `cluster_bridge_sankey_links.csv`",
        "- `layered_knowledge_graph_nodes.csv`",
        "- `layered_knowledge_graph_edges.csv`",
        "- `layered_knowledge_graph_v2_nodes.csv`",
        "- `layered_knowledge_graph_v2_edges.csv`",
        "- `layered_knowledge_graph_v2_layers.csv`",
        "- `evidence_confidence_heatmap.csv`",
        "- `evidence_confidence_heatmap_aggregate.csv`",
        "- `bridge_fragility.csv`",
        "- `bridge_fragility_segments.csv`",
        "- `claim_corroboration_matrix.csv`",
        "- `claim_corroboration_edges.csv`",
        "- `source_quality_dashboard.csv`",
        "- `sixdof_path_atlas.csv`",
        "- `sixdof_path_segments.csv`",
        "- `contradiction_boundary_overlay.csv`",
        "- `temporal_cluster_swimlanes.csv`",
        "- `relationship_type_treemap.csv`",
        "- `person_source_bipartite.csv`",
        "- `person_source_bipartite_nodes.csv`",
        "- `person_source_bipartite_edges.csv`",
        "- `public_narrative_readiness.csv`",
        "",
        "## Guardrails",
        "",
        "- These charts are evidence-navigation tools, not proof of a unified conspiracy.",
        "- Category bridges remain distinct from direct personal or institutional relationships.",
        "- Relationship classes separate documented succession, method diffusion, personnel bridges, narrative inheritance, contested overlap, and hypotheses requiring more sources.",
        "- Lead-only and boundary rows must remain visible when interpreting PROMIS/Maxwell, Barr/Epstein, and methodology-influence lanes.",
    ]
    (out / "analysis_charts.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"Exported analysis charts to {out}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="True Crime / Cult-Origin Research CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init-case", help="Create a case workspace")
    p.add_argument("case_dir")
    p.add_argument("--title", default=None)
    p.add_argument("--scope", default=None)
    p.add_argument("--public-interest", default=None)
    p.set_defaults(func=init_case)

    p = sub.add_parser("add-source", help="Register a source manually")
    p.add_argument("case_dir")
    p.add_argument("--title", required=True)
    p.add_argument("--url", default=None)
    p.add_argument("--source-type", default="news_article")
    p.add_argument("--reliability-grade", default="C", choices=["A", "B", "C", "D", "X"])
    p.add_argument("--author", default=None)
    p.add_argument("--publisher", default=None)
    p.add_argument("--date-published", default=None)
    p.add_argument("--archive-url", default=None)
    p.add_argument("--notes", default="")
    p.add_argument("--no-public-export", action="store_true")
    p.set_defaults(func=add_source)

    p = sub.add_parser("ingest-url", help="Fetch URL, extract text, and register as a source")
    p.add_argument("case_dir")
    p.add_argument("url")
    p.add_argument("--title", default=None)
    p.add_argument("--source-type", default="news_article")
    p.add_argument("--reliability-grade", default="C", choices=["A", "B", "C", "D", "X"])
    p.add_argument("--author", default=None)
    p.add_argument("--publisher", default=None)
    p.add_argument("--date-published", default=None)
    p.add_argument("--archive-url", default=None)
    p.add_argument("--notes", default="")
    p.add_argument("--timeout", type=int, default=25)
    p.add_argument("--no-public-export", action="store_true")
    p.set_defaults(func=ingest_url)

    p = sub.add_parser("draft-extraction", help="Create a structured extraction JSON packet for a source")
    p.add_argument("case_dir")
    p.add_argument("source_id")
    p.add_argument("--excerpt-chars", type=int, default=6000)
    p.add_argument("--template", choices=sorted(EXTRACTION_TEMPLATE_FILES), default="generic", help="Extraction packet template.")
    p.set_defaults(func=draft_extraction)

    p = sub.add_parser("ner-suggest", help="Generate crude named-entity/date suggestions from source text")
    p.add_argument("case_dir")
    p.add_argument("--source-id", default=None)
    p.add_argument("--limit", type=int, default=80)
    p.set_defaults(func=ner_suggest)

    p = sub.add_parser("link-names", help="Link a list of names to existing events and co-mentions")
    p.add_argument("case_dir")
    p.add_argument("--name", action="append", default=[], help="Name to link. Use 'Primary|Alias|Alias' for aliases.")
    p.add_argument("--names-file", action="append", default=[], help="File with one name per line. Aliases use '|'.")
    p.set_defaults(func=link_names)

    p = sub.add_parser("import-extraction", help="Import a filled extraction JSON packet into JSONL records")
    p.add_argument("case_dir")
    p.add_argument("extraction_json")
    p.set_defaults(func=import_extraction)

    p = sub.add_parser("validate", help="Validate case records")
    p.add_argument("case_dir")
    p.set_defaults(func=validate)

    p = sub.add_parser("dedupe", help="Report duplicate candidate entities, sources, or claims")
    p.add_argument("case_dir")
    p.add_argument("--record-type", choices=["all", "entities", "sources", "claims"], default="all")
    p.add_argument("--min-key-chars", type=int, default=12, help="Minimum normalized key length for candidate matching.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/dedupe_report_<date>.json.")
    p.set_defaults(func=dedupe)

    p = sub.add_parser("preserve-source", help="Hash and report preservation metadata for an existing source")
    p.add_argument("case_dir")
    p.add_argument("source_id")
    p.add_argument("--archive-url", default=None, help="Archive URL to store on the source before preservation reporting.")
    p.add_argument("--content-type", default=None, help="Content type to store on the source before preservation reporting.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/source_preservation/<source_id>.json.")
    p.set_defaults(func=preserve_source)

    p = sub.add_parser("resolve-identities", help="Report candidate duplicate or ambiguous identity records without merging")
    p.add_argument("case_dir")
    p.add_argument("--min-key-chars", type=int, default=8, help="Minimum normalized name/alias length for identity candidate matching.")
    p.add_argument("--include-merged", action="store_true", help="Include entity rows already marked status=merged.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/identity_resolution_<date>.json.")
    p.set_defaults(func=resolve_identities)

    p = sub.add_parser("audit-contradictions", help="Report explicit and likely claim contradictions without mutating claims")
    p.add_argument("case_dir")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/claim_contradiction_audit.json.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false in contradiction checks.")
    p.add_argument("--min-overlap", type=float, default=0.45, help="Minimum token overlap for likely contradiction pair checks.")
    p.add_argument("--fail-on-flags", action="store_true", help="Exit nonzero when any contradiction flag is found.")
    p.set_defaults(func=audit_contradictions)

    p = sub.add_parser("plan-public-records", help="Write a public-record source-lane plan for a subject")
    p.add_argument("case_dir")
    p.add_argument("--subject", required=True, help="Person, organization, place, event, or question subject to route.")
    p.add_argument("--question", default="", help="Optional research question or scope note.")
    p.add_argument("--lane", action="append", choices=sorted(PUBLIC_RECORD_LANES), default=[], help="Force one or more source lanes instead of keyword inference.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/public_records_plan_<subject>_<date>.json.")
    p.set_defaults(func=plan_public_records)

    p = sub.add_parser("index-transcript", help="Index timestamp and speaker-line candidates from a source text transcript")
    p.add_argument("case_dir")
    p.add_argument("source_id")
    p.add_argument("--max-segments", type=int, default=200, help="Maximum transcript segments to include in the candidate report.")
    p.add_argument("--include-private", action="store_true", help="Include a source marked public_export=false for internal review.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/transcript_index_<source_id>_<date>.json.")
    p.set_defaults(func=index_transcript)

    p = sub.add_parser("plan-open-records", help="Write a FOIA/open-records request plan for an agency and subject")
    p.add_argument("case_dir")
    p.add_argument("--subject", required=True, help="Subject of the request.")
    p.add_argument("--agency", required=True, help="Agency or public body receiving the request.")
    p.add_argument("--jurisdiction", default=None, help="Jurisdiction or office scope to include in the plan.")
    p.add_argument("--law", default=None, help="FOIA, sunshine, or open-records law to cite once confirmed.")
    p.add_argument("--date-range", default=None, help="Date range or temporal scope for responsive records.")
    p.add_argument("--record", action="append", default=[], help="Requested record category. Repeat for multiple categories.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/open_records_plan_<subject>_<date>.json.")
    p.set_defaults(func=plan_open_records)

    p = sub.add_parser("review-narrative-readiness", help="Report public narrative readiness gaps across claims, events, and relationships")
    p.add_argument("case_dir")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false in readiness checks.")
    p.add_argument("--require-spans", action="store_true", help="Flag claims/events without source_span_ids.")
    p.add_argument("--min-independent-sources", type=int, default=2, help="Independent source count expected for corroborated claims and allegations.")
    p.add_argument("--fail-on-blockers", action="store_true", help="Exit nonzero when blocker issues are found.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/narrative_readiness_review.json.")
    p.set_defaults(func=review_narrative_readiness)

    p = sub.add_parser("audit-privacy-redactions", help="Report privacy and redaction issues before public output")
    p.add_argument("case_dir")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false in the scan.")
    p.add_argument("--require-redaction-log", action="store_true", help="Warn when no redaction records exist.")
    p.add_argument("--warn-only", action="store_true", help="Write the report but do not exit nonzero on issues.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/privacy_redaction_audit.json.")
    p.set_defaults(func=audit_privacy_redactions)

    p = sub.add_parser("audit-public-export", help="Fail if public exports include unsafe or unsupported records")
    p.add_argument("case_dir")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/public_export_audit.json.")
    p.add_argument("--warn-only", action="store_true", help="Write the report but do not exit nonzero on issues.")
    p.set_defaults(func=audit_public_export)

    p = sub.add_parser("audit-source-independence", aliases=["source-independence"], help="Report source-chain, wire-copy, and press-release independence risks")
    p.add_argument("case_dir")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/source_independence_report.json.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false in record support checks.")
    p.add_argument("--min-title-chars", type=int, default=16, help="Minimum normalized title length for repeated-copy checks.")
    p.add_argument("--fail-on-flags", action="store_true", help="Exit nonzero when any source-independence flag is found.")
    p.set_defaults(func=source_independence)

    p = sub.add_parser("export-manim", help="Export public-safe Manim-ready CSVs")
    p.add_argument("case_dir")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private analysis only.")
    p.set_defaults(func=export_manim)

    p = sub.add_parser("export-timeline", help="Export cross-case timeline and claim corroboration CSVs")
    p.add_argument("cases_root", help="A cases directory or a single case workspace")
    p.add_argument("--out-dir", default=None, help="Output directory. Defaults to <kit>/data/exports/timeline for a cases root.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private review only.")
    p.set_defaults(func=export_timeline)

    p = sub.add_parser("export-case-charts", help="Export people-only graph and subcase timeline chart artifacts")
    p.add_argument("case_dir")
    p.add_argument("--out-dir", default=None, help="Output directory. Defaults to data/cases/<case>/exports/charts.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private review only.")
    p.set_defaults(func=export_case_charts)

    p = sub.add_parser("export-analysis-charts", help="Export extended analysis chart CSVs and dashboard")
    p.add_argument("case_dir")
    p.add_argument("--out-dir", default=None, help="Output directory. Defaults to data/cases/<case>/exports/analysis_charts.")
    p.add_argument("--clusters-dir", default=None, help="Cluster CSV directory. Defaults to data/cases/<case>/exports/clusters.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private review only.")
    p.set_defaults(func=export_analysis_charts)

    p = sub.add_parser("export-people-clusters", help="Run evidence-weighted Leiden clustering and graph-kernel/KDE analysis on people graph")
    p.add_argument("case_dir")
    p.add_argument("--out-dir", default=None, help="Output directory. Defaults to data/cases/<case>/exports/clusters.")
    p.add_argument("--charts-dir", default=None, help="People chart input/output directory. Defaults to data/cases/<case>/exports/charts.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private review only.")
    p.add_argument("--resolution", type=float, default=1.0, help="Leiden resolution parameter.")
    p.add_argument("--seed", type=int, default=7, help="Leiden random seed.")
    p.add_argument("--sigma", type=float, default=None, help="Kernel bandwidth. Defaults to median finite graph distance.")
    p.set_defaults(func=export_people_clusters)

    p = sub.add_parser("report", help="Write Markdown evidence board")
    p.add_argument("case_dir")
    p.set_defaults(func=report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except CasefileError as exc:
        raise SystemExit(str(exc)) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
