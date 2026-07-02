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
from adapters.ops.evidence.reports.analysis.command.builders.facets.people import (  # noqa: E402
    build_fragility,
    build_person_source_products,
)
from adapters.ops.evidence.reports.analysis.command.builders.facets.relationships import build_relation_type_counts  # noqa: E402
from adapters.ops.evidence.reports.analysis.command.builders.facets.timelines import build_swimlanes  # noqa: E402
from adapters.ops.evidence.reports.analysis.command.builders.layered import build_layered_graphs  # noqa: E402
from adapters.ops.evidence.reports.analysis.command.builders.paths import build_path_atlas  # noqa: E402
from adapters.ops.evidence.reports.analysis.command.context import load_analysis_context  # noqa: E402
from adapters.ops.evidence.reports.analysis.command.output import write_analysis_outputs  # noqa: E402
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

    relation_type_counts = build_relation_type_counts(ctx)

    person_products = build_person_source_products(ctx)
    person_source = person_products["person_source"]
    person_source_nodes = person_products["person_source_nodes"]

    readiness_products = build_readiness_products(ctx)
    readiness_rows = readiness_products["readiness_rows"]
    readiness_counts = readiness_products["readiness_counts"]

    fragility = build_fragility(edge_load)

    products = {
        "sankey_nodes": sankey_nodes,
        "cluster_bridge_links": cluster_bridge_links,
        "cluster_bridge_rows": cluster_bridge_rows,
        "bridge_segment_rows": bridge_segment_rows,
        "layered_nodes": layered_nodes,
        "layered_edges": layered_edges,
        "layered_v2_nodes": layered_v2_nodes,
        "layered_v2_edges": layered_v2_edges,
        "layered_v2_layers": layered_v2_layers,
        "claim_heatmap": claim_heatmap,
        "heatmap_aggregate": heatmap_aggregate,
        "fragility": fragility,
        "claim_matrix": claim_matrix,
        "claim_edge_rows": claim_edge_rows,
        "source_grade_count_rows": source_grade_count_rows,
        "source_dashboard": source_dashboard,
        "path_atlas": path_atlas,
        "path_segments": path_segments,
        "boundary_rows": boundary_rows,
        "swimlanes": swimlanes,
        "relation_type_counts": relation_type_counts,
        "person_source": person_source,
        "person_source_nodes": person_source_nodes,
        "readiness_rows": readiness_rows,
        "readiness_counts": readiness_counts,
    }
    write_analysis_outputs(ctx, products)


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
