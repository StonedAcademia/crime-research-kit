#!/usr/bin/env python3
"""True Crime / Cult-Origin Research CLI.

This tool is intentionally simple and local-first. It helps a Codex agent create
case folders, register public sources, stage source extraction, import structured
JSON records, validate JSONL files, and export Manim-ready CSVs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
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
from adapters.ops.evidence.reports.analysis.relationships import relation_family, relationship_class  # noqa: E402
from adapters.ops.evidence.reports.analysis.svg.base import chart_with_preview, short_label  # noqa: E402
from adapters.ops.evidence.reports.analysis.svg.facets import (  # noqa: E402
    render_bipartite_svg,
    render_boundary_overlay_svg,
    render_path_atlas_svg,
    render_swimlanes_svg,
    render_treemap_svg,
)
from adapters.ops.evidence.reports.analysis.svg.matrix import (  # noqa: E402
    render_claim_matrix_svg,
    render_fragility_svg,
    render_heatmap_svg,
    render_readiness_svg,
    render_source_quality_svg,
)
from adapters.ops.evidence.reports.analysis.svg.network.bridges import render_sankey_svg  # noqa: E402
from adapters.ops.evidence.reports.analysis.svg.network.layers import (  # noqa: E402
    render_layered_graph_svg,
    render_layered_graph_v2_svg,
)
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

def ensure_case(case_dir: str | Path) -> None:
    cdir = case_path(case_dir)
    if not (cdir / "case.json").exists():
        raise SystemExit(f"Not a case workspace: {cdir}. Run init-case first.")


def chart_row_table(rows: list[dict[str, Any]], columns: list[str], limit: int = 25) -> str:
    display_rows = rows[:limit]
    if not display_rows:
        return "<p class=\"muted\">No rows.</p>"
    head = "".join(f"<th>{html.escape(col.replace('_', ' ').title())}</th>" for col in columns)
    body = []
    for row in display_rows:
        cells = "".join(f"<td>{html.escape(flatten(row.get(col)))}</td>" for col in columns)
        body.append(f"<tr>{cells}</tr>")
    extra = f"<p class=\"muted\">Showing {len(display_rows)} of {len(rows)} rows.</p>" if len(rows) > limit else ""
    return f"<div class=\"table-wrap\"><table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>{extra}"


def simple_bar_rows(rows: list[dict[str, Any]], label_key: str, value_key: str, color_key: str | None = None, limit: int = 20) -> str:
    if not rows:
        return "<p class=\"muted\">No rows.</p>"
    max_value = max((parse_float(row.get(value_key), 0.0) for row in rows), default=1.0) or 1.0
    parts = []
    for row in rows[:limit]:
        value = parse_float(row.get(value_key), 0.0)
        width = max(2.0, 100.0 * value / max_value)
        color_class = slugify(str(row.get(color_key or label_key, "bar")), 24)
        parts.append(
            "<div class=\"bar-row\">"
            f"<span class=\"bar-label\">{html.escape(str(row.get(label_key, '')))}</span>"
            f"<span class=\"bar-track\"><span class=\"bar-fill c-{color_class}\" style=\"width:{width:.1f}%\"></span></span>"
            f"<span class=\"bar-value\">{html.escape(str(row.get(value_key, '')))}</span>"
            "</div>"
        )
    return "".join(parts)


def analysis_chart_files() -> list[tuple[str, str]]:
    return [
        ("Cluster Bridge Sankey", "cluster_bridge_sankey_nodes.csv / cluster_bridge_sankey_links.csv"),
        ("Layered Knowledge Graph", "layered_knowledge_graph_nodes.csv / layered_knowledge_graph_edges.csv"),
        ("Layered Knowledge Graph v2", "layered_knowledge_graph_v2_nodes.csv / layered_knowledge_graph_v2_edges.csv / layered_knowledge_graph_v2_layers.csv"),
        ("Evidence Confidence Heatmap", "evidence_confidence_heatmap.csv / evidence_confidence_heatmap_aggregate.csv"),
        ("Bridge Fragility", "bridge_fragility.csv / bridge_fragility_segments.csv"),
        ("Claim Corroboration Matrix", "claim_corroboration_matrix.csv / claim_corroboration_edges.csv"),
        ("Source Quality Dashboard", "source_quality_dashboard.csv"),
        ("6DOF Path Atlas", "sixdof_path_atlas.csv / sixdof_path_segments.csv"),
        ("Contradiction / Boundary Overlay", "contradiction_boundary_overlay.csv"),
        ("Temporal Cluster Swimlanes", "temporal_cluster_swimlanes.csv"),
        ("Relationship-Class Treemap", "relationship_type_treemap.csv"),
        ("Person-Source Bipartite Graph", "person_source_bipartite_nodes.csv / person_source_bipartite_edges.csv"),
        ("Public Narrative Readiness", "public_narrative_readiness.csv"),
    ]


def analysis_chart_css() -> str:
    return """
<style>
:root { color-scheme: light; --ink:#182026; --muted:#5d6975; --line:#d9e1e8; --panel:#f8fafc; --accent:#2b6cb0; --good:#237a57; --warn:#b7791f; --bad:#a63a3a; --soft:#eef4fa; }
body { margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color:var(--ink); background:#fff; }
header { padding:28px 36px 18px; border-bottom:1px solid var(--line); background:var(--panel); }
main { padding:24px 36px 56px; max-width:1440px; margin:0 auto; }
h1 { margin:0 0 8px; font-size:26px; letter-spacing:0; }
h2 { margin:0 0 10px; font-size:19px; letter-spacing:0; }
h3 { margin:18px 0 8px; font-size:14px; letter-spacing:0; }
p, li { color:var(--muted); line-height:1.45; }
a { color:var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; }
.grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap:18px; align-items:stretch; }
section, .card { border:1px solid var(--line); border-radius:8px; padding:16px; background:#fff; overflow:hidden; }
.card { display:flex; flex-direction:column; min-height:160px; }
.card-link { margin-top:auto; font-weight:700; }
.wide { grid-column:1 / -1; }
.muted { color:var(--muted); font-size:13px; }
.toolbar { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:16px 0; }
.toolbar input { min-width:260px; flex:1; border:1px solid var(--line); border-radius:6px; padding:9px 10px; font:inherit; }
.toolbar button, .back-link { border:1px solid var(--line); border-radius:6px; background:#fff; color:#283542; padding:8px 10px; font:inherit; font-size:12px; cursor:pointer; }
.toolbar button:hover, .toolbar button[aria-pressed="true"] { background:var(--soft); border-color:#a9bdcf; }
.chart-layout { display:grid; grid-template-columns:minmax(0, 1fr) 320px; gap:16px; align-items:start; }
.inspector { border:1px solid var(--line); border-radius:8px; padding:14px; background:#fbfdff; position:sticky; top:16px; min-height:160px; }
.inspector-title { margin:0 0 8px; font-size:13px; font-weight:800; }
.inspector-body { color:var(--muted); font-size:13px; line-height:1.45; overflow-wrap:anywhere; }
.table-wrap { overflow:auto; border:1px solid var(--line); border-radius:6px; }
table { border-collapse:collapse; width:100%; min-width:720px; font-size:12px; }
th, td { padding:7px 8px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
th { background:var(--soft); color:#24313d; position:sticky; top:0; }
code { background:#edf2f7; padding:1px 4px; border-radius:4px; }
.chart-shell { width:100%; overflow:hidden; border:1px solid var(--line); border-radius:8px; background:#fff; margin:8px 0 12px; }
.chart-shell.scroll-x { overflow-x:auto; }
.chart-svg { display:block; width:100%; height:auto; min-height:240px; }
.chart-bg { fill:#fbfdff; }
.axis { stroke:#93a4b4; stroke-width:1.2; }
.axis-label { fill:#465461; font-size:12px; font-weight:650; }
.node-label { fill:#1f2933; font-size:12px; font-weight:650; }
.mini-label { fill:#53616f; font-size:10.5px; }
.heat-label { fill:#111827; font-size:11px; font-weight:700; }
.warn-label { fill:var(--bad); font-size:11px; font-weight:800; }
.metric { fill:#16202a; font-size:27px; font-weight:800; }
.node-box { fill:#fff; stroke:#bac8d6; stroke-width:1.2; }
.treemap-label { fill:#111827; font-size:10px; font-weight:700; pointer-events:none; }
.data-preview { margin-top:14px; }
.data-preview summary { cursor:pointer; color:var(--muted); font-size:12px; font-weight:700; }
.interactive-mark { cursor:pointer; outline:none; transform-box:fill-box; transform-origin:center; transition:opacity .16s ease, filter .16s ease, stroke-width .16s ease, transform .16s ease; }
.interactive-mark:hover, .interactive-mark:focus { filter:drop-shadow(0 0 5px rgba(43,108,176,.62)); transform:scale(1.035); }
.interactive-mark.is-selected { filter:drop-shadow(0 0 9px rgba(35,122,87,.78)); opacity:1 !important; stroke:#111827 !important; stroke-width:2.4 !important; transform:scale(1.07); animation:selectedPulse 1.25s ease-in-out infinite; }
.interactive-mark.is-related { filter:drop-shadow(0 0 5px rgba(183,121,31,.45)); opacity:.82 !important; }
.interactive-mark.is-dim { opacity:.1 !important; filter:grayscale(.85); }
.inspector.is-live { border-color:#9fb8ce; box-shadow:0 8px 24px rgba(35,52,68,.08); }
.inspector.is-selected { border-color:#88b4a1; box-shadow:0 10px 28px rgba(35,122,87,.12); }
.chart-tooltip { position:fixed; z-index:20; max-width:360px; pointer-events:none; background:#17212b; color:#fff; border-radius:7px; padding:8px 10px; font-size:12px; line-height:1.35; box-shadow:0 10px 26px rgba(10,22,34,.24); opacity:0; transform:translate(10px, 12px); transition:opacity .12s ease, transform .12s ease; overflow-wrap:anywhere; }
.chart-tooltip.is-visible { opacity:.96; transform:translate(12px, 14px); }
.click-flash { position:fixed; z-index:19; width:10px; height:10px; border-radius:999px; pointer-events:none; border:2px solid rgba(43,108,176,.55); transform:translate(-50%, -50%) scale(1); animation:clickFlash .48s ease-out forwards; }
@keyframes selectedPulse { 0%, 100% { filter:drop-shadow(0 0 7px rgba(35,122,87,.55)); } 50% { filter:drop-shadow(0 0 13px rgba(35,122,87,.9)); } }
@keyframes clickFlash { to { opacity:0; transform:translate(-50%, -50%) scale(9); } }
@media (prefers-reduced-motion: reduce) { .interactive-mark, .chart-tooltip, .click-flash { transition:none; animation:none; } .interactive-mark:hover, .interactive-mark:focus, .interactive-mark.is-selected { transform:none; } }
@media (max-width: 900px) { header, main { padding-left:18px; padding-right:18px; } .chart-layout { grid-template-columns:1fr; } .inspector { position:static; } }
</style>
"""


def analysis_chart_script() -> str:
    return """
<script>
(() => {
  const inspector = document.querySelector('[data-inspector]');
  const inspectorBody = document.querySelector('[data-inspector-body]');
  const search = document.querySelector('[data-search]');
  const reset = document.querySelector('[data-reset]');
  const tooltip = document.createElement('div');
  tooltip.className = 'chart-tooltip';
  tooltip.setAttribute('role', 'status');
  document.body.appendChild(tooltip);
  const marks = Array.from(document.querySelectorAll('svg title'))
    .map((title) => title.parentElement)
    .filter(Boolean);
  const stopWords = new Set(['with', 'from', 'this', 'that', 'source', 'status', 'claim', 'event', 'path', 'record', 'count', 'context', 'bridge']);
  function detailFor(el) {
    const title = el.querySelector('title');
    return title ? title.textContent.trim() : '';
  }
  function compactDetail(text, limit = 360) {
    if (!text) return '';
    return text.length > limit ? `${text.slice(0, limit - 1)}...` : text;
  }
  function tokensFor(text) {
    return new Set(
      (text || '')
        .toLowerCase()
        .split(/[^a-z0-9_:-]+/)
        .filter((token) => token.length > 3 && !stopWords.has(token))
        .slice(0, 36)
    );
  }
  function setInspector(text, mode = 'live') {
    if (!inspectorBody) return;
    inspectorBody.textContent = text || 'Hover or click a chart mark to inspect the row, path, source, or status behind it.';
    if (inspector) {
      inspector.classList.toggle('is-live', Boolean(text) && mode === 'live');
      inspector.classList.toggle('is-selected', Boolean(text) && mode === 'selected');
    }
  }
  function eventPoint(event) {
    const target = event && event.target && event.target.getBoundingClientRect ? event.target.getBoundingClientRect() : null;
    const x = event && Number.isFinite(event.clientX) && event.clientX ? event.clientX : (target ? target.right : 24);
    const y = event && Number.isFinite(event.clientY) && event.clientY ? event.clientY : (target ? target.top : 24);
    return { x, y };
  }
  function showTooltip(text, event) {
    if (!text || !event) return;
    const point = eventPoint(event);
    tooltip.textContent = compactDetail(text, 220);
    tooltip.style.left = `${Math.max(8, Math.min(window.innerWidth - 390, point.x + 12))}px`;
    tooltip.style.top = `${Math.max(8, Math.min(window.innerHeight - 140, point.y + 12))}px`;
    tooltip.classList.add('is-visible');
  }
  function hideTooltip() {
    tooltip.classList.remove('is-visible');
  }
  function clickFlash(event) {
    if (!event) return;
    const point = eventPoint(event);
    const flash = document.createElement('span');
    flash.className = 'click-flash';
    flash.style.left = `${point.x}px`;
    flash.style.top = `${point.y}px`;
    document.body.appendChild(flash);
    window.setTimeout(() => flash.remove(), 520);
  }
  function selectMark(el, event) {
    const selectedText = detailFor(el);
    const selectedTokens = tokensFor(selectedText);
    let relatedCount = 0;
    marks.forEach((mark) => {
      mark.classList.remove('is-selected', 'is-related', 'is-dim');
      if (mark === el) return;
      const otherTokens = tokensFor(detailFor(mark));
      const related = [...selectedTokens].some((token) => otherTokens.has(token));
      if (related) {
        mark.classList.add('is-related');
        relatedCount += 1;
      } else {
        mark.classList.add('is-dim');
      }
    });
    el.classList.add('is-selected');
    setInspector(`${selectedText}${relatedCount ? `\n\nRelated marks highlighted: ${relatedCount}` : ''}`, 'selected');
    clickFlash(event);
    showTooltip(selectedText, event);
  }
  function applyQuery(query) {
    const q = (query || '').trim().toLowerCase();
    marks.forEach((el) => {
      const text = detailFor(el).toLowerCase();
      const visible = !q || text.includes(q);
      if (!el.classList.contains('is-selected')) {
        el.classList.toggle('is-dim', !visible);
      }
    });
  }
  marks.forEach((el) => {
    el.classList.add('interactive-mark');
    el.setAttribute('tabindex', '0');
    el.setAttribute('role', 'button');
    el.setAttribute('aria-label', compactDetail(detailFor(el), 120));
    el.addEventListener('mouseenter', (event) => {
      setInspector(detailFor(el), 'live');
      showTooltip(detailFor(el), event);
    });
    el.addEventListener('mousemove', (event) => showTooltip(detailFor(el), event));
    el.addEventListener('mouseleave', hideTooltip);
    el.addEventListener('focus', (event) => {
      setInspector(detailFor(el), 'live');
      showTooltip(detailFor(el), event);
    });
    el.addEventListener('blur', hideTooltip);
    el.addEventListener('click', (event) => {
      event.stopPropagation();
      selectMark(el, event);
    });
    el.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        selectMark(el, event);
      }
    });
  });
  if (search) {
    search.addEventListener('input', () => applyQuery(search.value));
  }
  document.querySelectorAll('[data-query]').forEach((button) => {
    button.addEventListener('click', () => {
      const value = button.getAttribute('data-query') || '';
      if (search) search.value = value;
      document.querySelectorAll('[data-query]').forEach((btn) => btn.setAttribute('aria-pressed', 'false'));
      button.setAttribute('aria-pressed', 'true');
      applyQuery(value);
      setInspector(value ? `Filtered marks containing: ${value}` : '');
    });
  });
  if (reset) {
    reset.addEventListener('click', () => {
      if (search) search.value = '';
      hideTooltip();
      marks.forEach((mark) => mark.classList.remove('is-dim', 'is-selected', 'is-related'));
      document.querySelectorAll('[data-query]').forEach((btn) => btn.setAttribute('aria-pressed', 'false'));
      setInspector('');
    });
  }
  setInspector('');
})();
</script>
"""


def filter_terms(rows: list[dict[str, Any]], keys: list[str], limit: int = 10) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in keys:
            values = parse_cell_list(row.get(key)) or [str(row.get(key, ""))]
            for value in values:
                text = str(value).strip()
                if not text or text in seen or len(text) > 48:
                    continue
                seen.add(text)
                terms.append(text)
                if len(terms) >= limit:
                    return terms
    return terms


def build_analysis_chart_specs(chart_data: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted([
        {
            "number": 1,
            "title": "Cluster Bridge Sankey",
            "filename": "01_cluster_bridge_sankey.html",
            "description": "Audited inter-cluster bridge flow with category and lead-context links visually separated.",
            "csvs": "cluster_bridge_sankey_nodes.csv / cluster_bridge_sankey_links.csv",
            "chart_html": render_sankey_svg(chart_data["sankey_nodes"], chart_data["cluster_bridge_links"]),
            "preview_html": chart_row_table(chart_data["cluster_bridges"], ["src_cluster", "dst_cluster", "bridge_class", "hops", "path", "statuses"], 12),
            "filters": filter_terms(chart_data["cluster_bridge_links"], ["public_readiness", "bridge_class"]),
        },
        {
            "number": 2,
            "title": "Layered Knowledge Graph",
            "filename": "02_layered_knowledge_graph.html",
            "description": "Layered graph separating people, events, organizations, institutions, and context nodes.",
            "csvs": "layered_knowledge_graph_nodes.csv / layered_knowledge_graph_edges.csv",
            "chart_html": render_layered_graph_svg(chart_data["layered_nodes"], chart_data["layered_edges"]),
            "preview_html": chart_row_table(chart_data["layered_edges"], ["src_label", "dst_label", "edge_type", "relation_type", "relationship_class", "status", "source_count"], 18),
            "filters": filter_terms(chart_data["layered_edges"], ["status", "edge_type", "relation_type", "relationship_class"]),
        },
        {
            "number": 13,
            "title": "Layered Knowledge Graph v2",
            "filename": "13_layered_knowledge_graph_v2.html",
            "description": "Evidence-navigation graph with explicit layers, source grades, public-readiness state, caveats, and cluster context.",
            "csvs": "layered_knowledge_graph_v2_nodes.csv / layered_knowledge_graph_v2_edges.csv / layered_knowledge_graph_v2_layers.csv",
            "chart_html": render_layered_graph_v2_svg(chart_data["layered_v2_nodes"], chart_data["layered_v2_edges"]),
            "preview_html": chart_row_table(chart_data["layered_v2_edges"], ["src_label", "dst_label", "relationship_class", "bridge_class", "readiness", "source_count", "caveat"], 18),
            "filters": filter_terms(chart_data["layered_v2_edges"], ["readiness", "bridge_class", "relationship_class", "best_source_grade", "caveat"]),
        },
        {
            "number": 3,
            "title": "Evidence Confidence Heatmap",
            "filename": "03_evidence_confidence_heatmap.html",
            "description": "Claim-type by status heatmap, with cell intensity tied to average confidence.",
            "csvs": "evidence_confidence_heatmap.csv / evidence_confidence_heatmap_aggregate.csv",
            "chart_html": render_heatmap_svg(chart_data["heatmap_aggregate"]),
            "preview_html": chart_row_table(chart_data["claim_heatmap"], ["claim_id", "status", "confidence", "source_count", "best_source_grade", "readiness"], 18),
            "filters": filter_terms(chart_data["claim_heatmap"], ["status", "claim_type", "readiness"]),
        },
        {
            "number": 4,
            "title": "Bridge Fragility Chart",
            "filename": "04_bridge_fragility.html",
            "description": "Load-bearing bridge records plotted against fragility score.",
            "csvs": "bridge_fragility.csv / bridge_fragility_segments.csv",
            "chart_html": render_fragility_svg(chart_data["fragility"]),
            "preview_html": chart_row_table(chart_data["fragility"], ["record_id", "relationship_class", "load_bearing_score", "fragility_score", "fragility_tier", "bridge_class"], 18),
            "filters": filter_terms(chart_data["fragility"], ["fragility_tier", "bridge_class", "relationship_class", "status"]),
        },
        {
            "number": 5,
            "title": "Claim Corroboration Matrix",
            "filename": "05_claim_corroboration_matrix.html",
            "description": "Claim-source matrix colored by source grade and preserving boundary/contradiction markers.",
            "csvs": "claim_corroboration_matrix.csv / claim_corroboration_edges.csv",
            "chart_html": render_claim_matrix_svg(chart_data["claim_matrix"]),
            "preview_html": chart_row_table(chart_data["claim_matrix"], ["claim_id", "source_id", "source_grade", "source_type", "claim_status"], 20),
            "filters": filter_terms(chart_data["claim_matrix"], ["source_grade", "claim_status", "source_role"]),
        },
        {
            "number": 6,
            "title": "Source Quality Dashboard",
            "filename": "06_source_quality_dashboard.html",
            "description": "Source-grade distribution with coverage footprint across claims, events, relationships, and people.",
            "csvs": "source_quality_dashboard.csv",
            "chart_html": render_source_quality_svg(chart_data["source_grade_counts"], chart_data["source_dashboard"]),
            "preview_html": chart_row_table(chart_data["source_dashboard"], ["source_id", "reliability_grade", "claim_count", "event_count", "relationship_count", "nonpublic_record_count"], 18),
            "filters": filter_terms(chart_data["source_dashboard"], ["reliability_grade", "source_type", "publisher"]),
        },
        {
            "number": 7,
            "title": "6DOF Path Atlas",
            "filename": "07_sixdof_path_atlas.html",
            "description": "Hop-distance atlas from the anchor person, with paths over six hops explicitly marked.",
            "csvs": "sixdof_path_atlas.csv / sixdof_path_segments.csv",
            "chart_html": render_path_atlas_svg(chart_data["path_atlas"]),
            "preview_html": chart_row_table(chart_data["path_atlas"], ["target_person", "hops", "over_six_hops", "weakest_status", "relationship_classes"], 18),
            "filters": filter_terms(chart_data["path_atlas"], ["weakest_status", "bridge_classes", "relationship_classes", "over_six_hops"]),
        },
        {
            "number": 8,
            "title": "Contradiction / Boundary Overlay",
            "filename": "08_contradiction_boundary_overlay.html",
            "description": "Boundary and contradiction markers grouped by record type and status.",
            "csvs": "contradiction_boundary_overlay.csv",
            "chart_html": render_boundary_overlay_svg(chart_data["boundary_rows"]),
            "preview_html": chart_row_table(chart_data["boundary_rows"], ["record_id", "record_type", "status", "claim_type", "boundary_kind", "relationship_class", "summary"], 18),
            "filters": filter_terms(chart_data["boundary_rows"], ["record_type", "status", "boundary_kind", "relationship_class"]),
        },
        {
            "number": 9,
            "title": "Temporal Cluster Swimlanes",
            "filename": "09_temporal_cluster_swimlanes.html",
            "description": "Dated event-link markers placed on one swimlane per cluster.",
            "csvs": "temporal_cluster_swimlanes.csv",
            "chart_html": render_swimlanes_svg(chart_data["swimlanes"]),
            "preview_html": chart_row_table(chart_data["swimlanes"], ["cluster_id", "start_date", "event_id", "event_title", "relationship_class", "status", "source_count"], 18),
            "filters": filter_terms(chart_data["swimlanes"], ["cluster_id", "status", "event_link_status", "relation_type", "relationship_class"]),
        },
        {
            "number": 10,
            "title": "Relationship-Class Treemap",
            "filename": "10_relationship_type_treemap.html",
            "description": "Weighted relationship/event-link buckets grouped by lineage, diffusion, personnel, narrative, contested, and hypothesis classes.",
            "csvs": "relationship_type_treemap.csv",
            "chart_html": render_treemap_svg(chart_data["relation_type_counts"]),
            "preview_html": chart_row_table(chart_data["relation_type_counts"], ["relationship_class", "relation_family", "relation_type", "status", "weighted_count", "row_count"], 18),
            "filters": filter_terms(chart_data["relation_type_counts"], ["relationship_class", "relation_family", "status", "public_scope"]),
        },
        {
            "number": 11,
            "title": "Person-Source Bipartite Graph",
            "filename": "11_person_source_bipartite.html",
            "description": "Top person-source evidence links derived from direct, claim, relationship, event, and event-link paths.",
            "csvs": "person_source_bipartite_nodes.csv / person_source_bipartite_edges.csv",
            "chart_html": render_bipartite_svg(chart_data["person_source_nodes"], chart_data["person_source"]),
            "preview_html": chart_row_table(chart_data["person_source"], ["person_name", "source_id", "source_grade", "contexts"], 18),
            "filters": filter_terms(chart_data["person_source"], ["source_grade", "contexts", "public_evidence_state"]),
        },
        {
            "number": 12,
            "title": "Public Narrative Readiness",
            "filename": "12_public_narrative_readiness.html",
            "description": "Readiness tiers for public narration, with privacy and boundary gates preserved.",
            "csvs": "public_narrative_readiness.csv",
            "chart_html": render_readiness_svg(chart_data["readiness_counts"]),
            "preview_html": chart_row_table(chart_data["readiness_counts"], ["readiness", "count"], 12),
            "filters": filter_terms(chart_data["readiness_counts"], ["readiness"]),
        },
    ], key=lambda spec: int(spec["number"]))


def render_analysis_chart_page(case_title: str, include_private: bool, spec: dict[str, Any]) -> str:
    generated = dt.datetime.now(dt.timezone.utc).isoformat()
    filter_buttons = "".join(
        f'<button type="button" data-query="{html.escape(term)}" aria-pressed="false">{html.escape(short_label(term, 22))}</button>'
        for term in spec.get("filters", [])
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(spec["title"])} - {html.escape(case_title)}</title>
{analysis_chart_css()}
</head>
<body>
<header>
<p><a class="back-link" href="analysis_charts.html">Back to chart index</a></p>
<h1>{int(spec["number"])}. {html.escape(spec["title"])}</h1>
<p>{html.escape(spec["description"])}</p>
<p>Generated {html.escape(generated)}. Scope: {'public and private/internal rows' if include_private else 'public-export rows only'}.</p>
<p>CSV source: <code>{html.escape(spec["csvs"])}</code></p>
</header>
<main>
<section>
<div class="toolbar">
<input type="search" data-search placeholder="Filter visible marks by label, status, source, claim, or path">
{filter_buttons}
<button type="button" data-query="" aria-pressed="false">All</button>
<button type="button" data-reset>Reset selection</button>
</div>
<div class="chart-layout">
<div>
{spec["chart_html"]}
<details class="data-preview"><summary>Data preview</summary>{spec["preview_html"]}</details>
</div>
<aside class="inspector" data-inspector>
<p class="inspector-title">Inspector</p>
<div class="inspector-body" data-inspector-body></div>
</aside>
</div>
</section>
</main>
{analysis_chart_script()}
</body>
</html>
"""


def render_analysis_dashboard(case_title: str, include_private: bool, chart_specs: list[dict[str, Any]]) -> str:
    generated = dt.datetime.now(dt.timezone.utc).isoformat()
    file_rows = "".join(
        f"<li><code>{html.escape(name)}</code> - {html.escape(path)}</li>"
        for name, path in analysis_chart_files()
    )
    cards = "".join(
        '<article class="card">'
        f'<h2>{int(spec["number"])}. {html.escape(spec["title"])}</h2>'
        f'<p>{html.escape(spec["description"])}</p>'
        f'<p class="muted"><code>{html.escape(spec["csvs"])}</code></p>'
        f'<a class="card-link" href="{html.escape(spec["filename"])}">Open interactive chart</a>'
        "</article>"
        for spec in chart_specs
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Analysis chart index - {html.escape(case_title)}</title>
{analysis_chart_css()}
</head>
<body>
<header>
<h1>Analysis charts: {html.escape(case_title)}</h1>
<p>Generated {html.escape(generated)}. Scope: {'public and private/internal rows' if include_private else 'public-export rows only'}.</p>
<p>Open each chart in its own page for data-derived filters, hover/click inspection, keyboard focus, and collapsible table previews.</p>
</header>
<main>
<section class="wide"><h2>Files</h2><ul>{file_rows}</ul></section>
<div class="grid">{cards}</div>
</main>
</body>
</html>
"""


def export_analysis_charts(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    enforce_public_output_gate(args.case_dir, "export-analysis-charts", args.include_private)
    cdir = case_path(args.case_dir)
    include_private = args.include_private
    out = Path(args.out_dir).expanduser().resolve() if args.out_dir else cdir / "exports" / "analysis_charts"
    out.mkdir(parents=True, exist_ok=True)

    case_meta = json.loads((cdir / "case.json").read_text(encoding="utf-8"))
    case_title = str(case_meta.get("title", cdir.name))
    sources = public_rows(read_jsonl(record_path(cdir, "sources")), include_private)
    entities = public_rows(read_jsonl(record_path(cdir, "entities")), include_private)
    claims = public_rows(read_jsonl(record_path(cdir, "claims")), include_private)
    events = public_rows(read_jsonl(record_path(cdir, "events")), include_private)
    event_links = public_rows(read_jsonl(record_path(cdir, "event_links")), include_private)
    relationships = public_rows(read_jsonl(record_path(cdir, "relationships")), include_private)

    source_by_id = {str(source.get("source_id")): source for source in sources}
    claim_by_id = {str(claim.get("claim_id")): claim for claim in claims}
    entity_by_id = {str(entity.get("entity_id")): entity for entity in entities}
    people = [entity for entity in entities if entity.get("entity_type") == "person"]
    people_by_id = {str(person.get("entity_id")): person for person in people}

    clusters_dir = Path(args.clusters_dir).expanduser().resolve() if args.clusters_dir else cdir / "exports" / "clusters"
    cluster_by_person: dict[str, str] = {}
    if (clusters_dir / "people_clusters.csv").exists():
        for row in read_csv_dicts(clusters_dir / "people_clusters.csv"):
            cluster_by_person[str(row.get("entity_id"))] = str(row.get("cluster_id") or "")
    if not cluster_by_person:
        for idx, person in enumerate(sorted(people, key=entity_display), start=1):
            cluster_by_person[str(person.get("entity_id"))] = f"P{idx}"

    cluster_summary, cluster_labels = read_cluster_metadata(clusters_dir)
    audit_cluster_labels, audit_bridges = parse_cluster_bridge_audit(cdir)
    cluster_labels.update(audit_cluster_labels)

    graph, graph_meta = analysis_graph(entities, events, event_links, relationships)
    for person_id, cluster_id in cluster_by_person.items():
        if person_id in graph_meta:
            graph_meta[person_id]["cluster_id"] = cluster_id

    cluster_members: dict[str, list[str]] = {}
    for person_id, cluster_id in cluster_by_person.items():
        if person_id in people_by_id:
            cluster_members.setdefault(cluster_id, []).append(person_id)

    cluster_ids = sorted(cluster_members)
    sankey_nodes: list[dict[str, Any]] = []
    for cluster_id in cluster_ids:
        members = sorted(cluster_members[cluster_id], key=lambda person_id: entity_display(people_by_id.get(person_id)))
        summary = cluster_summary.get(cluster_id, {})
        sankey_nodes.append({
            "cluster_id": cluster_id,
            "cluster_label": cluster_labels.get(cluster_id, summary.get("label") or summary.get("members") or cluster_id),
            "member_entity_ids": members,
            "member_names": [entity_display(people_by_id.get(person_id)) for person_id in members],
            "size": len(members),
            "mean_kde_density": summary.get("mean_kde_density", ""),
            "internal_edge_weight": summary.get("internal_edge_weight", ""),
            "boundary_edge_weight": summary.get("boundary_edge_weight", ""),
            "notes": "cluster from people_clusters.csv" if cluster_summary else "fallback one-person cluster",
        })

    cluster_bridge_rows: list[dict[str, Any]] = []
    cluster_bridge_links: list[dict[str, Any]] = []
    bridge_segment_rows: list[dict[str, Any]] = []
    edge_load: dict[str, dict[str, Any]] = {}
    path_atlas: list[dict[str, Any]] = []
    path_segments: list[dict[str, Any]] = []

    def node_label(node_id: str) -> str:
        return str(graph_meta.get(node_id, {}).get("label", node_id))

    def path_label(steps: list[tuple[str, str, dict[str, Any]]]) -> str:
        if not steps:
            return ""
        return " -> ".join([node_label(steps[0][0]), *[node_label(step[1]) for step in steps]])

    audit_by_pair = {(row["src_cluster"], row["dst_cluster"]): row for row in audit_bridges}
    bridge_pairs = list(audit_by_pair) if audit_by_pair else list(combinations(cluster_ids, 2))
    for left, right in bridge_pairs:
        steps = shortest_analysis_path(graph, cluster_members[left], cluster_members[right])
        audit_row = audit_by_pair.get((left, right), {})
        if steps is None and not audit_row:
            continue
        steps = steps or []
        statuses = sorted({str(step[2].get("status", "")) for step in steps})
        relationship_classes = sorted({
            relationship_class(step[2], str(step[2].get("edge_type", "relationship")))
            for step in steps
        })
        source_ids = sorted({sid for step in steps for sid in parse_cell_list(step[2].get("source_ids"))})
        if audit_row.get("audit_source_ids"):
            source_ids = sorted(set(source_ids) | set(parse_cell_list(audit_row.get("audit_source_ids"))))
        claim_ids = sorted({cid for step in steps for cid in parse_cell_list(step[2].get("claim_ids"))})
        source_rows = [source_by_id[sid] for sid in source_ids if sid in source_by_id]
        boundary_claim_ids = sorted(
            claim_id for claim_id in claim_ids
            if claim_id in claim_by_id and boundary_signal(claim_by_id[claim_id])
        )
        bridge_class = audit_bridge_class(str(audit_row.get("capacity", ""))) if audit_row else classify_bridge_path(steps, graph_meta)
        path_text = path_label(steps) or str(audit_row.get("audit_path", ""))
        public_export = all(step[2].get("public_export", True) is not False for step in steps) if steps else bool(audit_row)
        is_lead_bridge = "lead" in " ".join([str(audit_row.get("capacity", "")), str(audit_row.get("boundary_text", "")), bridge_class]).lower()
        row = {
            "bridge_id": audit_row.get("bridge_id") or f"B_{left}_{right}_{slugify(bridge_class, 32).upper()}",
            "src_cluster": left,
            "dst_cluster": right,
            "src_cluster_label": cluster_labels.get(left, left),
            "dst_cluster_label": cluster_labels.get(right, right),
            "bridge_class": bridge_class,
            "relationship_classes": relationship_classes,
            "hops": len(steps),
            "path": path_text,
            "statuses": statuses,
            "source_ids": source_ids,
            "claim_ids": claim_ids,
            "boundary_claim_ids": boundary_claim_ids,
            "boundary_text": audit_row.get("boundary_text", ""),
            "source_grade_counts": source_grade_counts(source_rows),
            "public_readiness": "lead_or_disputed" if is_lead_bridge else readiness_label({"status": weakest_status(statuses) or "single_source", "public_export": public_export}, source_rows),
            "public_export": public_export,
            "notes": audit_row.get("capacity", ""),
        }
        cluster_bridge_rows.append(row)
        cluster_bridge_links.append(row)
        for src, dst, edge in steps:
            record_id = str(edge.get("record_id", ""))
            if not record_id:
                continue
            bridge_segment_rows.append({
                "bridge_id": row["bridge_id"],
                "segment_index": len([segment for segment in bridge_segment_rows if segment.get("bridge_id") == row["bridge_id"]]) + 1,
                "src_id": src,
                "src_label": node_label(src),
                "dst_id": dst,
                "dst_label": node_label(dst),
                "record_type": edge.get("edge_type", ""),
                "record_id": record_id,
                "relation_type": edge.get("relation_type", ""),
                "relationship_class": edge.get("relationship_class") or relationship_class(edge, str(edge.get("edge_type", "relationship"))),
                "status": edge.get("status", ""),
                "confidence": edge.get("confidence", ""),
                "source_ids": parse_cell_list(edge.get("source_ids")),
                "claim_ids": parse_cell_list(edge.get("claim_ids")),
                "public_export": edge.get("public_export", True),
                "guardrail_note": "lead/category/context edge; do not read as direct personal tie" if classify_bridge_path([(src, dst, edge)], graph_meta) != "direct_or_near_direct" else "",
            })
            load = edge_load.setdefault(record_id, {
                "record_id": record_id,
                "edge_type": edge.get("edge_type", ""),
                "relation_type": edge.get("relation_type", ""),
                "relationship_class": edge.get("relationship_class") or relationship_class(edge, str(edge.get("edge_type", "relationship"))),
                "status": edge.get("status", ""),
                "source_ids": set(),
                "claim_ids": set(),
                "load_bearing_score": 0,
                "bridge_classes": set(),
                "example_path": path_label(steps),
            })
            load["load_bearing_score"] += 1
            load["bridge_classes"].add(bridge_class)
            load.setdefault("relationship_classes", set()).add(edge.get("relationship_class") or relationship_class(edge, str(edge.get("edge_type", "relationship"))))
            load["source_ids"].update(parse_cell_list(edge.get("source_ids")))
            load["claim_ids"].update(parse_cell_list(edge.get("claim_ids")))

    anchor_id = "E_BILL_W" if "E_BILL_W" in people_by_id else (sorted(people_by_id, key=lambda eid: entity_display(people_by_id[eid]))[0] if people_by_id else "")
    if anchor_id:
        for person_id, person in sorted(people_by_id.items(), key=lambda item: entity_display(item[1])):
            if person_id == anchor_id:
                continue
            steps = shortest_analysis_path(graph, [anchor_id], [person_id])
            if steps is None:
                continue
            statuses = [str(step[2].get("status", "")) for step in steps]
            path_id = f"P_{slugify(entity_display(people_by_id[anchor_id]), 24).upper()}_{slugify(entity_display(person), 24).upper()}"
            path_atlas.append({
                "path_id": path_id,
                "anchor_person": entity_display(people_by_id[anchor_id]),
                "target_person": entity_display(person),
                "target_entity_id": person_id,
                "target_cluster": cluster_by_person.get(person_id, ""),
                "hops": len(steps),
                "over_six_hops": len(steps) > 6,
                "path": path_label(steps),
                "weakest_status": min(statuses, key=lambda status: STATUS_SCORE.get(status, 0.0)) if statuses else "",
                "bridge_classes": sorted({classify_bridge_path([step], graph_meta) for step in steps}),
                "relationship_classes": sorted({
                    relationship_class(step[2], str(step[2].get("edge_type", "relationship")))
                    for step in steps
                }),
                "source_ids": sorted({sid for step in steps for sid in parse_cell_list(step[2].get("source_ids"))}),
                "claim_ids": sorted({cid for step in steps for cid in parse_cell_list(step[2].get("claim_ids"))}),
                "caveat": "Contains category/context bridges; path length is not evidence of influence, guilt, membership, or control.",
            })
            for idx, (src, dst, edge) in enumerate(steps, start=1):
                step_class = classify_bridge_path([(src, dst, edge)], graph_meta)
                path_segments.append({
                    "path_id": path_id,
                    "segment_index": idx,
                    "src_id": src,
                    "src_label": node_label(src),
                    "dst_id": dst,
                    "dst_label": node_label(dst),
                    "src_cluster": graph_meta.get(src, {}).get("cluster_id", ""),
                    "dst_cluster": graph_meta.get(dst, {}).get("cluster_id", ""),
                    "record_type": edge.get("edge_type", ""),
                    "record_id": edge.get("record_id", ""),
                    "relation_type": edge.get("relation_type", ""),
                    "relationship_class": edge.get("relationship_class") or relationship_class(edge, str(edge.get("edge_type", "relationship"))),
                    "segment_status": edge.get("status", ""),
                    "segment_confidence": edge.get("confidence", ""),
                    "segment_public_export": edge.get("public_export", True),
                    "source_ids": parse_cell_list(edge.get("source_ids")),
                    "claim_ids": parse_cell_list(edge.get("claim_ids")),
                    "is_category_bridge": step_class == "category_bridge",
                    "is_context_only": step_class in {"category_bridge", "institutional_software_bridge", "lead_context_bridge", "indirect_context_bridge"},
                    "caveat": "context/category/lead edge" if step_class != "direct_or_near_direct" else "",
                })

    layered_nodes: list[dict[str, Any]] = []
    for node_id, meta in sorted(graph_meta.items(), key=lambda item: (item[1].get("layer", ""), item[1].get("label", ""))):
        source_ids = parse_cell_list(entity_by_id.get(node_id, {}).get("source_ids")) if node_id in entity_by_id else []
        layered_nodes.append({
            "node_id": node_id,
            "label": meta.get("label", ""),
            "layer": meta.get("layer", ""),
            "cluster_id": meta.get("cluster_id", ""),
            "status": entity_by_id.get(node_id, {}).get("status", ""),
            "source_count": len(source_ids),
            "public_export": entity_by_id.get(node_id, {}).get("public_export", True),
        })
    seen_edges: set[tuple[str, str, str]] = set()
    layered_edges: list[dict[str, Any]] = []
    for src, edges in graph.items():
        for dst, edge in edges:
            key = tuple(sorted([src, dst]) + [str(edge.get("record_id", ""))])
            if key in seen_edges:
                continue
            seen_edges.add(key)
            layered_edges.append({
                "src_id": src,
                "dst_id": dst,
                "src_label": node_label(src),
                "dst_label": node_label(dst),
                "edge_type": edge.get("edge_type", ""),
                "relation_type": edge.get("relation_type", ""),
                "relationship_class": edge.get("relationship_class") or relationship_class(edge, str(edge.get("edge_type", "relationship"))),
                "status": edge.get("status", ""),
                "confidence": edge.get("confidence", ""),
                "source_count": len(parse_cell_list(edge.get("source_ids"))),
                "source_ids": parse_cell_list(edge.get("source_ids")),
                "claim_ids": parse_cell_list(edge.get("claim_ids")),
                "public_export": edge.get("public_export", True),
            })

    layer_order_map = {
        "person": 1,
        "institution": 2,
        "organization": 3,
        "group": 4,
        "event_series": 5,
        "event": 6,
        "object": 7,
        "publication": 8,
        "document": 9,
        "place_alias": 10,
        "entity": 11,
    }
    event_record_by_node = {"EVENT:" + str(event.get("event_id")): event for event in events}
    degree_by_node: dict[str, int] = {}
    for edge in layered_edges:
        degree_by_node[str(edge.get("src_id", ""))] = degree_by_node.get(str(edge.get("src_id", "")), 0) + 1
        degree_by_node[str(edge.get("dst_id", ""))] = degree_by_node.get(str(edge.get("dst_id", "")), 0) + 1

    def source_rows_for_ids(source_ids: Iterable[str]) -> list[dict[str, Any]]:
        return [source_by_id[sid] for sid in source_ids if sid in source_by_id]

    def independent_count(source_rows: list[dict[str, Any]]) -> int:
        return len({source_independence_key(source) for source in source_rows})

    def node_evidence_state(record: dict[str, Any], source_rows: list[dict[str, Any]]) -> str:
        if record.get("public_export", True) is False:
            return "internal_only"
        status = str(record.get("status", ""))
        if status == "candidate":
            return "candidate_or_identity_review"
        if not source_rows:
            return "unsourced_context"
        grade = best_grade(source_rows)
        if grade in {"A", "B"}:
            return "documented_source"
        return "source_note_required"

    def caveat_for_edge(edge: dict[str, Any], source_rows: list[dict[str, Any]], boundary_claim_ids: list[str], bridge_class: str) -> str:
        status = str(edge.get("status", ""))
        edge_class = str(edge.get("relationship_class", ""))
        if edge.get("public_export", True) is False:
            return "Internal-only edge; do not use in public narrative without review."
        if edge_class == "hypothesis_requires_more_sources" or status == "unverified":
            return "Hypothesis/lead; needs more independent sources."
        if edge_class == "contested_overlap" or status == "disputed" or boundary_claim_ids:
            return "Contested or boundary-marked edge; narrate with the dispute."
        if bridge_class not in {"direct_or_near_direct", "documented_successor_bridge"}:
            return "Context/category/method bridge; not a direct personal tie."
        if len(source_rows) <= 1 or status == "single_source":
            return "Single-source edge; verify before public narrative use."
        return ""

    layered_v2_nodes: list[dict[str, Any]] = []
    for row in layered_nodes:
        node_id = str(row.get("node_id", ""))
        record = entity_by_id.get(node_id) or event_record_by_node.get(node_id) or {}
        source_ids = parse_cell_list(record.get("source_ids"))
        claim_ids = parse_cell_list(record.get("claim_ids"))
        node_sources = source_rows_for_ids(source_ids)
        readiness = readiness_label(record, node_sources) if record else "review_needed"
        layer = str(row.get("layer") or "entity")
        evidence_state = node_evidence_state(record, node_sources)
        boundary = boundary_signal(record) if record else False
        layered_v2_nodes.append({
            "node_id": node_id,
            "label": row.get("label", ""),
            "layer": layer,
            "layer_order": layer_order_map.get(layer, 99),
            "cluster_id": row.get("cluster_id", ""),
            "status": record.get("status", row.get("status", "")),
            "degree": degree_by_node.get(node_id, 0),
            "source_count": len(source_ids),
            "independent_source_count": independent_count(node_sources),
            "best_source_grade": best_grade(node_sources),
            "source_grade_counts": source_grade_counts(node_sources),
            "claim_count": len(claim_ids),
            "evidence_state": evidence_state,
            "readiness": readiness,
            "boundary_flag": boundary,
            "public_export": record.get("public_export", row.get("public_export", True)),
            "caveat": "Boundary/context node; inspect source chain before narration." if boundary or evidence_state in {"candidate_or_identity_review", "unsourced_context"} else "",
        })

    layered_v2_edges: list[dict[str, Any]] = []
    for idx, edge in enumerate(layered_edges, start=1):
        source_ids = set(parse_cell_list(edge.get("source_ids")))
        claim_ids = parse_cell_list(edge.get("claim_ids"))
        boundary_claim_ids: list[str] = []
        for claim_id in claim_ids:
            claim = claim_by_id.get(claim_id)
            if not claim:
                continue
            source_ids.update(parse_cell_list(claim.get("source_ids")))
            if boundary_signal(claim):
                boundary_claim_ids.append(claim_id)
        edge_sources = source_rows_for_ids(sorted(source_ids))
        src_id = str(edge.get("src_id", ""))
        dst_id = str(edge.get("dst_id", ""))
        graph_edge = {
            "record_id": edge.get("edge_id") or edge.get("record_id") or f"LKG2_{idx}",
            "edge_type": edge.get("edge_type", ""),
            "relation_type": edge.get("relation_type", ""),
            "relationship_class": edge.get("relationship_class", ""),
            "status": edge.get("status", ""),
            "source_ids": sorted(source_ids),
            "claim_ids": claim_ids,
            "confidence": edge.get("confidence", ""),
            "notes": "",
            "public_export": edge.get("public_export", True),
        }
        bridge_class = classify_bridge_path([(src_id, dst_id, graph_edge)], graph_meta)
        readiness = readiness_label(graph_edge, edge_sources)
        evidence_weight = round(
            STATUS_SCORE.get(str(edge.get("status", "")), 0.35)
            * max(0.35, source_grade_score(edge_sources))
            * (1.0 + min(4, len(edge_sources)) * 0.12),
            3,
        )
        caveat = caveat_for_edge(graph_edge, edge_sources, boundary_claim_ids, bridge_class)
        layered_v2_edges.append({
            "edge_id": graph_edge["record_id"],
            "src_id": src_id,
            "dst_id": dst_id,
            "src_label": edge.get("src_label", ""),
            "dst_label": edge.get("dst_label", ""),
            "src_layer": graph_meta.get(src_id, {}).get("layer", ""),
            "dst_layer": graph_meta.get(dst_id, {}).get("layer", ""),
            "edge_type": edge.get("edge_type", ""),
            "relation_type": edge.get("relation_type", ""),
            "relationship_class": edge.get("relationship_class", ""),
            "relation_family": relation_family(str(edge.get("relation_type", "")), str(edge.get("edge_type", ""))),
            "bridge_class": bridge_class,
            "status": edge.get("status", ""),
            "confidence": edge.get("confidence", ""),
            "evidence_weight": evidence_weight,
            "source_count": len(edge_sources),
            "independent_source_count": independent_count(edge_sources),
            "best_source_grade": best_grade(edge_sources),
            "source_grade_counts": source_grade_counts(edge_sources),
            "claim_ids": claim_ids,
            "source_ids": sorted(source_ids),
            "boundary_claim_ids": sorted(boundary_claim_ids),
            "readiness": readiness,
            "boundary_flag": bool(boundary_claim_ids) or boundary_signal(graph_edge),
            "public_export": edge.get("public_export", True),
            "caveat": caveat,
        })

    layer_summary_map: dict[str, dict[str, Any]] = {}
    for node in layered_v2_nodes:
        layer = str(node.get("layer", "entity"))
        bucket = layer_summary_map.setdefault(layer, {
            "layer": layer,
            "layer_order": node.get("layer_order", 99),
            "node_count": 0,
            "public_node_count": 0,
            "internal_node_count": 0,
            "candidate_node_count": 0,
            "source_count": 0,
            "edge_count": 0,
            "public_edge_count": 0,
            "lead_or_disputed_edge_count": 0,
            "public_ready_edge_count": 0,
            "_statuses": {},
            "_classes": {},
        })
        bucket["node_count"] += 1
        bucket["public_node_count"] += 1 if node.get("public_export", True) is not False else 0
        bucket["internal_node_count"] += 1 if node.get("public_export", True) is False else 0
        bucket["candidate_node_count"] += 1 if str(node.get("status", "")) == "candidate" else 0
        bucket["source_count"] += int(node.get("source_count", 0) or 0)
    for edge in layered_v2_edges:
        for layer_key in ["src_layer", "dst_layer"]:
            layer = str(edge.get(layer_key) or "entity")
            bucket = layer_summary_map.setdefault(layer, {
                "layer": layer,
                "layer_order": layer_order_map.get(layer, 99),
                "node_count": 0,
                "public_node_count": 0,
                "internal_node_count": 0,
                "candidate_node_count": 0,
                "source_count": 0,
                "edge_count": 0,
                "public_edge_count": 0,
                "lead_or_disputed_edge_count": 0,
                "public_ready_edge_count": 0,
                "_statuses": {},
                "_classes": {},
            })
            bucket["edge_count"] += 1
            bucket["public_edge_count"] += 1 if edge.get("public_export", True) is not False else 0
            bucket["lead_or_disputed_edge_count"] += 1 if str(edge.get("readiness", "")) == "lead_or_disputed" else 0
            bucket["public_ready_edge_count"] += 1 if str(edge.get("readiness", "")) == "public_ready" else 0
            status = str(edge.get("status", "") or "unknown")
            rel_class = str(edge.get("relationship_class", "") or "unknown")
            bucket["_statuses"][status] = bucket["_statuses"].get(status, 0) + 1
            bucket["_classes"][rel_class] = bucket["_classes"].get(rel_class, 0) + 1
    layered_v2_layers = []
    for row in sorted(layer_summary_map.values(), key=lambda item: (int(parse_float(item.get("layer_order"), 99)), str(item.get("layer", "")))):
        statuses = sorted(row.pop("_statuses").items(), key=lambda item: (-item[1], item[0]))
        classes = sorted(row.pop("_classes").items(), key=lambda item: (-item[1], item[0]))
        row["dominant_statuses"] = ";".join(f"{key}:{value}" for key, value in statuses[:5])
        row["dominant_relationship_classes"] = ";".join(f"{key}:{value}" for key, value in classes[:5])
        layered_v2_layers.append(row)

    claim_heatmap: list[dict[str, Any]] = []
    claim_matrix: list[dict[str, Any]] = []
    claim_edge_rows: list[dict[str, Any]] = []
    for claim in sorted(claims, key=lambda row: str(row.get("claim_id", ""))):
        source_ids = [sid for sid in parse_cell_list(claim.get("source_ids")) if sid in source_by_id]
        source_rows = [source_by_id[sid] for sid in source_ids]
        independent_count = len({source_independence_key(src) for src in source_rows})
        claim_heatmap.append({
            "claim_id": claim.get("claim_id", ""),
            "claim": claim.get("claim", ""),
            "claim_type": claim.get("claim_type", ""),
            "status": claim.get("status", ""),
            "confidence": claim.get("confidence", ""),
            "status_score": STATUS_SCORE.get(str(claim.get("status", "")), 0.0),
            "source_count": len(source_rows),
            "independent_source_count": independent_count,
            "best_source_grade": best_grade(source_rows),
            "source_grade_counts": source_grade_counts(source_rows),
            "source_grade_score": source_grade_score(source_rows),
            "privacy_review": claim.get("privacy_review", ""),
            "public_export": claim.get("public_export", True),
            "boundary_flag": boundary_signal(claim),
            "readiness": readiness_label(claim, source_rows),
        })
        for source in source_rows:
            claim_matrix.append({
                "claim_id": claim.get("claim_id", ""),
                "claim_label": str(claim.get("claim", ""))[:160],
                "source_id": source.get("source_id", ""),
                "source_title": source.get("title", ""),
                "source_grade": source.get("reliability_grade", ""),
                "source_type": source.get("source_type", ""),
                "source_publisher": source.get("publisher", ""),
                "claim_status": claim.get("status", ""),
                "claim_confidence": claim.get("confidence", ""),
                "claim_type": claim.get("claim_type", ""),
                "source_role": "boundary_source" if boundary_signal(claim) else "direct_support",
                "safe_public_cell": public_ready_record(claim) and source.get("public_export", True) is not False,
                "boundary_flag": boundary_signal(claim),
                "contradiction_flag": bool(parse_cell_list(claim.get("contradicts"))),
                "contradicts": claim.get("contradicts", []),
                "supports": claim.get("supports", []),
            })
        for edge_type, linked_ids in [("supports", parse_cell_list(claim.get("supports"))), ("contradicts", parse_cell_list(claim.get("contradicts")))]:
            for linked_id in linked_ids:
                linked = claim_by_id.get(linked_id, {})
                claim_edge_rows.append({
                    "from_claim_id": claim.get("claim_id", ""),
                    "to_claim_id": linked_id,
                    "edge_type": edge_type,
                    "from_claim_status": claim.get("status", ""),
                    "to_claim_status": linked.get("status", ""),
                    "from_confidence": claim.get("confidence", ""),
                    "to_confidence": linked.get("confidence", ""),
                    "shared_source_count": len(set(source_ids) & set(parse_cell_list(linked.get("source_ids")))),
                    "from_source_ids": source_ids,
                    "to_source_ids": parse_cell_list(linked.get("source_ids")),
                    "boundary_flag": edge_type == "contradicts" or boundary_signal(claim) or boundary_signal(linked),
                    "safe_public_pair": public_ready_record(claim) and (not linked or public_ready_record(linked)),
                })

    heatmap_groups: dict[tuple[str, str], dict[str, Any]] = {}
    for row in claim_heatmap:
        key = (str(row.get("claim_type") or "unknown"), str(row.get("status") or "unknown"))
        group = heatmap_groups.setdefault(key, {
            "claim_type": key[0],
            "status": key[1],
            "claim_count": 0,
            "public_claim_count": 0,
            "internal_only_count": 0,
            "needs_review_count": 0,
            "confidence_total": 0.0,
            "source_count_total": 0,
            "a_sources": 0,
            "b_sources": 0,
            "c_sources": 0,
            "d_sources": 0,
            "boundary_claim_count": 0,
            "claim_ids": [],
        })
        group["claim_count"] += 1
        group["public_claim_count"] += 1 if row.get("public_export") is not False else 0
        group["internal_only_count"] += 1 if row.get("public_export") is False else 0
        group["needs_review_count"] += 1 if row.get("privacy_review") and row.get("privacy_review") != "clear" else 0
        group["confidence_total"] += parse_float(row.get("confidence"), 0.0)
        group["source_count_total"] += int(row.get("source_count") or 0)
        group["boundary_claim_count"] += 1 if row.get("boundary_flag") else 0
        group["claim_ids"].append(row.get("claim_id", ""))
        grade_map = dict(part.split(":", 1) for part in str(row.get("source_grade_counts", "")).split(";") if ":" in part)
        group["a_sources"] += int(grade_map.get("A", "0"))
        group["b_sources"] += int(grade_map.get("B", "0"))
        group["c_sources"] += int(grade_map.get("C", "0"))
        group["d_sources"] += int(grade_map.get("D", "0"))
    heatmap_aggregate = []
    for group in heatmap_groups.values():
        count = max(1, int(group["claim_count"]))
        group["avg_confidence"] = round(float(group.pop("confidence_total")) / count, 3)
        group["avg_source_count"] = round(float(group["source_count_total"]) / count, 3)
        heatmap_aggregate.append(group)
    heatmap_aggregate.sort(key=lambda row: (str(row["claim_type"]), str(row["status"])))

    source_counter: dict[str, dict[str, Any]] = {
        sid: {
            "source_id": sid,
            "title": source.get("title", ""),
            "reliability_grade": source.get("reliability_grade", ""),
            "source_type": source.get("source_type", ""),
            "publisher": source.get("publisher", ""),
            "date_published": source.get("date_published", ""),
            "date_accessed": source.get("date_accessed", ""),
            "url": source.get("url", ""),
            "independence_group": source.get("independence_group", ""),
            "claim_count": 0,
            "event_count": 0,
            "event_link_count": 0,
            "relationship_count": 0,
            "entity_count": 0,
            "person_count": 0,
            "verified_claim_count": 0,
            "corroborated_claim_count": 0,
            "single_source_claim_count": 0,
            "disputed_claim_count": 0,
            "unverified_claim_count": 0,
            "needs_privacy_review_count": 0,
            "nonpublic_record_count": 0,
            "source_quality_notes": source.get("notes", ""),
            "public_export": source.get("public_export", True),
        }
        for sid, source in source_by_id.items()
    }
    for claim in claims:
        for sid in parse_cell_list(claim.get("source_ids")):
            if sid in source_counter:
                source_counter[sid]["claim_count"] += 1
                status_key = f"{claim.get('status', 'unknown')}_claim_count"
                if status_key in source_counter[sid]:
                    source_counter[sid][status_key] += 1
                if claim.get("privacy_review") and claim.get("privacy_review") != "clear":
                    source_counter[sid]["needs_privacy_review_count"] += 1
                if claim.get("public_export", True) is False:
                    source_counter[sid]["nonpublic_record_count"] += 1
    for event in events:
        for sid in parse_cell_list(event.get("source_ids")):
            if sid in source_counter:
                source_counter[sid]["event_count"] += 1
                if event.get("public_export", True) is False:
                    source_counter[sid]["nonpublic_record_count"] += 1
    for link in event_links:
        for sid in parse_cell_list(link.get("source_ids")):
            if sid in source_counter:
                source_counter[sid]["event_link_count"] += 1
                if link.get("public_export", True) is False:
                    source_counter[sid]["nonpublic_record_count"] += 1
    for rel in relationships:
        for sid in parse_cell_list(rel.get("source_ids")):
            if sid in source_counter:
                source_counter[sid]["relationship_count"] += 1
                if rel.get("public_export", True) is False:
                    source_counter[sid]["nonpublic_record_count"] += 1
    for entity in entities:
        for sid in parse_cell_list(entity.get("source_ids")):
            if sid in source_counter:
                source_counter[sid]["entity_count"] += 1
                if entity.get("public_export", True) is False:
                    source_counter[sid]["nonpublic_record_count"] += 1
    for person in people:
        for sid in parse_cell_list(person.get("source_ids")):
            if sid in source_counter:
                source_counter[sid]["person_count"] += 1
    source_dashboard = sorted(source_counter.values(), key=lambda row: (str(row["reliability_grade"]), str(row["source_id"])))
    grade_counts: dict[str, int] = {}
    for source in source_dashboard:
        grade = str(source.get("reliability_grade", ""))
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
    source_grade_count_rows = [{"grade": grade, "count": count} for grade, count in sorted(grade_counts.items())]

    boundary_rows: list[dict[str, Any]] = []
    for claim in claims:
        claim_type = str(claim.get("claim_type", ""))
        status = str(claim.get("status", ""))
        contradicts = parse_cell_list(claim.get("contradicts"))
        if claim_type == "contradiction_or_boundary" or contradicts or status in {"disputed", "unverified", "excluded_from_public_script"}:
            boundary_rows.append({
                "record_id": claim.get("claim_id", ""),
                "record_type": "claim",
                "status": status,
                "claim_type": claim_type,
                "boundary_kind": "contradicts" if contradicts else claim_type or status,
                "summary": claim.get("claim", ""),
                "source_ids": claim.get("source_ids", []),
                "contradicts": contradicts,
            })
    for rel in relationships:
        notes = str(rel.get("notes", "")).lower()
        if boundary_signal(rel) or any(term in notes for term in ["boundary", "lead", "alleged", "not verified", "do not treat"]):
            boundary_rows.append({
                "record_id": rel.get("rel_id", ""),
                "record_type": "relationship",
                "status": rel.get("status", ""),
                "claim_type": "",
                "boundary_kind": "relationship_note",
                "relationship_class": relationship_class(rel),
                "summary": rel.get("notes", ""),
                "source_ids": rel.get("source_ids", []),
                "contradicts": "",
            })
    for link in event_links:
        if boundary_signal(link):
            boundary_rows.append({
                "record_id": link.get("event_link_id", ""),
                "record_type": "event_link",
                "status": link.get("status", ""),
                "claim_type": "",
                "boundary_kind": "event_link_context",
                "relationship_class": relationship_class(link, "event_link"),
                "summary": link.get("notes", "") or link.get("basis", ""),
                "source_ids": link.get("source_ids", []),
                "contradicts": "",
            })

    swimlanes: list[dict[str, Any]] = []
    event_by_id = {str(event.get("event_id")): event for event in events}
    seen_swimlane_keys: set[tuple[str, str, str]] = set()
    for link in event_links:
        event_id = str(link.get("event_id", ""))
        event = event_by_id.get(event_id, {})
        entity_id = str(link.get("entity_id", ""))
        cluster_id = cluster_by_person.get(entity_id, "unclustered")
        key = (cluster_id, event_id, str(link.get("event_link_id", "")))
        seen_swimlane_keys.add(key)
        swimlanes.append({
            "cluster_id": cluster_id,
            "cluster_label": cluster_labels.get(cluster_id, cluster_id),
            "entity_id": entity_id,
            "name": entity_display(entity_by_id.get(entity_id)),
            "start_date": event.get("start_date", ""),
            "end_date": event.get("end_date", ""),
            "date_precision": event.get("date_precision", ""),
            "event_id": event_id,
            "event_title": event.get("title", ""),
            "event_type": event.get("event_type", ""),
            "status": event.get("status", ""),
            "confidence": event.get("confidence", ""),
            "event_link_id": link.get("event_link_id", ""),
            "relation_type": link.get("relation_type", ""),
            "relationship_class": relationship_class(link, "event_link"),
            "event_link_status": link.get("status", ""),
            "event_link_confidence": link.get("confidence", ""),
            "source_count": len(set(parse_cell_list(event.get("source_ids"))) | set(parse_cell_list(link.get("source_ids")))),
            "claim_ids": sorted(set(parse_cell_list(event.get("claim_ids"))) | set(parse_cell_list(link.get("claim_ids")))),
            "source_ids": sorted(set(parse_cell_list(event.get("source_ids"))) | set(parse_cell_list(link.get("source_ids")))),
            "is_public_safe": public_ready_record(event) and public_ready_record(link),
            "caveat": "co-mention/context link" if "co_mentioned" in str(link.get("relation_type", "")) else "",
        })
    for event in events:
        event_id = str(event.get("event_id", ""))
        for entity_id in parse_cell_list(event.get("entity_ids")) or [""]:
            cluster_id = cluster_by_person.get(entity_id, "unclustered")
            key = (cluster_id, event_id, "")
            if key in seen_swimlane_keys:
                continue
            swimlanes.append({
                "cluster_id": cluster_id,
                "cluster_label": cluster_labels.get(cluster_id, cluster_id),
                "entity_id": entity_id,
                "name": entity_display(entity_by_id.get(entity_id)),
                "start_date": event.get("start_date", ""),
                "end_date": event.get("end_date", ""),
                "date_precision": event.get("date_precision", ""),
                "event_id": event_id,
                "event_title": event.get("title", ""),
                "event_type": event.get("event_type", ""),
                "status": event.get("status", ""),
                "confidence": event.get("confidence", ""),
                "event_link_id": "",
                "relation_type": "event_entity",
                "relationship_class": "personnel_bridge",
                "event_link_status": "",
                "event_link_confidence": "",
                "source_count": len(parse_cell_list(event.get("source_ids"))),
                "claim_ids": event.get("claim_ids", []),
                "source_ids": event.get("source_ids", []),
                "is_public_safe": public_ready_record(event),
                "caveat": "",
            })
    swimlanes.sort(key=lambda row: (str(row["cluster_id"]), date_sort_key(row.get("start_date")), str(row["event_id"])))

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

    readiness_rows: list[dict[str, Any]] = []
    for record_type, rows, id_key in [
        ("claim", claims, "claim_id"),
        ("event", events, "event_id"),
        ("event_link", event_links, "event_link_id"),
        ("relationship", relationships, "rel_id"),
    ]:
        for row in rows:
            source_rows = [source_by_id[sid] for sid in parse_cell_list(row.get("source_ids")) if sid in source_by_id]
            boundary = boundary_signal(row)
            readiness_rows.append({
                "record_type": record_type,
                "record_id": row.get(id_key, ""),
                "status": row.get("status", ""),
                "confidence": row.get("confidence", ""),
                "source_count": len(source_rows),
                "best_source_grade": best_grade(source_rows),
                "source_grade_counts": source_grade_counts(source_rows),
                "public_export": row.get("public_export", True),
            "privacy_review": row.get("privacy_review", "clear"),
            "readiness": readiness_label(row, source_rows),
            "boundary_flag": boundary,
            "required_caveat": "Boundary/lead/context wording required." if boundary else "",
            "relationship_class": relationship_class(row, record_type) if record_type in {"event_link", "relationship"} else "",
            "summary": row.get("claim") or row.get("title") or row.get("notes", ""),
        })
    readiness_count_map: dict[str, int] = {}
    for row in readiness_rows:
        readiness = str(row.get("readiness", ""))
        readiness_count_map[readiness] = readiness_count_map.get(readiness, 0) + 1
    readiness_counts = [{"readiness": key, "count": value} for key, value in sorted(readiness_count_map.items())]

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
