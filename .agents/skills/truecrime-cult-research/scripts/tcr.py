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
from adapters.ops.evidence.reports.analysis.command.entry import export_analysis_charts  # noqa: E402
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
from adapters.interfaces.cli.entry import main  # noqa: E402
from adapters.interfaces.cli.parser import build_parser  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
