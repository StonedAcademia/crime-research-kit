import * as d3 from "d3";

import { detail, renderDetail, type DetailSearchContext } from "../detail";
import type { Row } from "../model";
import { inspector, text } from "../model";

export const PALETTE = ["#315b77", "#3b705c", "#9c5a39", "#8061a8", "#b9472d", "#65743a", "#8a5b80", "#4f6f8f", "#7a6a3b"];
const NETWORK_SEARCH_KEYS = [
  "label", "title", "record_id", "node_id", "cluster_id", "cluster_label", "source_title", "src_id", "src_label",
  "dst_id", "dst_label", "relationship_class", "relation_type", "edge_type", "layer", "record_type", "event_title",
  "event_type", "claim_label", "claim_type", "status", "confidence", "readiness", "facet_types", "top_facets",
  "caveat", "best_source_grade", "subproject_id", "subproject_label",
];

export function bindMark<GElement extends Element, PElement extends d3.BaseType, PDatum>(el: d3.Selection<GElement, Row, PElement, PDatum>, root: HTMLElement): void {
  el.classed("visual-mark", true)
    .attr("tabindex", 0)
    .attr("data-search", (row) => rowSearchText(row))
    .on("mouseenter focus click", (_, row) => {
      const body = inspector(root);
      if (body) renderDetail(body, row, "preview", detailSearchContext(root.dataset.visualSearchQuery || ""));
    });
}

export function svg(root: HTMLElement, width = 920, height = 470) {
  root.replaceChildren();
  return d3.select(root).append("svg").attr("viewBox", `0 0 ${width} ${height}`).attr("role", "img");
}

export function clusterColor(value: unknown): string {
  const raw = text(value || "cluster");
  let hash = 0;
  for (const char of raw) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return PALETTE[hash % PALETTE.length];
}

export function rowFacets(row: Row): string[] {
  return text(row.facet_types).split(";").map((item) => item.trim()).filter(Boolean);
}

export function searchTokens(query: string): string[] {
  return normalizeSearch(query).split(" ").filter(Boolean);
}

export function normalizeSearch(value: string): string {
  return value.toLowerCase()
    .replace(/[_:/|,;()[\]{}-]+/g, " ")
    .replace(/[^a-z0-9.]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function rowSearchText(row: Row): string {
  const keyed = NETWORK_SEARCH_KEYS.map((key) => row[key]);
  return normalizeSearch([detail(row), ...keyed, ...Object.values(row)].map((value) => text(value)).join(" "));
}

export function detailSearchContext(query: string, tokens = searchTokens(query)): DetailSearchContext | undefined {
  return tokens.length ? { query, tokens } : undefined;
}

export function metricValue(row: Row, key: string, fallback?: string): number {
  const raw = Number(row[key] ?? 0);
  if (Number.isFinite(raw) && raw > 0) return raw;
  const backup = fallback ? Number(row[fallback] ?? 0) : 0;
  return Number.isFinite(backup) ? backup : 0;
}

export function evidenceFootprint(row: Row): number {
  const explicit = Number(row.evidence_footprint_score ?? 0);
  if (Number.isFinite(explicit) && explicit > 0) return explicit;
  return (
    metricValue(row, "record_count", "node_count")
    + metricValue(row, "relationship_count", "edge_count")
    + metricValue(row, "claim_count")
    + metricValue(row, "source_count")
    + metricValue(row, "event_count")
  );
}

export function gradeWeight(value: unknown): number {
  const grade = text(value).trim().toUpperCase();
  if (grade === "A") return 5;
  if (grade === "B") return 4;
  if (grade === "C") return 3;
  if (grade === "D") return 2;
  if (grade === "X") return 1;
  return 0.8;
}

export function statusWeight(value: unknown): number {
  const status = text(value).toLowerCase();
  if (/(corroborated|verified|confirmed)/.test(status)) return 5;
  if (/(multiple|triangulated|supported)/.test(status)) return 4;
  if (/(single|candidate|review)/.test(status)) return 2.4;
  if (/(contested|contradict|disputed|blocked)/.test(status)) return 1.2;
  return 1.8;
}

export function truthy(value: unknown): boolean {
  return /^(true|1|yes)$/i.test(text(value).trim());
}

export function matrixKey(row: Row): string {
  return `${text(row.claim_id)}\u0000${text(row.source_id)}`;
}

export function sourceGradeColor(value: unknown): string {
  const grade = text(value).trim().toUpperCase();
  if (grade === "A") return "#315b77";
  if (grade === "B") return "#3b705c";
  if (grade === "C") return "#9c5a39";
  if (grade === "D") return "#b9472d";
  if (grade === "X") return "#65743a";
  return "#8aa39b";
}

export function countBy(rows: Row[], key: string): Map<string, number> {
  const counts = new Map<string, number>();
  for (const row of rows) {
    const value = text(row[key]);
    if (!value) continue;
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return counts;
}

export function modeButton(label: string): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  return button;
}
