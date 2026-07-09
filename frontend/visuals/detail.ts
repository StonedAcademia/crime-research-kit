import type { Row } from "./model";
import { short, text } from "./model";

const PRIMARY_KEYS = new Set([
  "best_source_grade", "caveat", "claim_count", "claim_type", "cluster_label", "confidence", "dst_label", "edge_count",
  "end_date", "event_count", "event_title", "event_type", "facet_types", "first_date", "independent_source_count", "label",
  "last_date", "layer", "node_count", "readiness", "record_id", "record_type", "relation_type", "relationship_class",
  "relationship_count", "source_count", "source_title", "src_label", "start_date", "status", "subproject_count", "title",
  "top_facets", "visible_edge_count",
]);

export type DetailMode = "preview" | "pinned";
export type DetailSearchContext = {
  query: string;
  tokens?: string[];
};

const MATCH_KEYS = [
  "label", "title", "record_id", "node_id", "cluster_label", "source_title", "src_label", "dst_label",
  "relationship_class", "relation_type", "edge_type", "layer", "record_type", "event_type", "claim_type",
  "status", "confidence", "readiness", "facet_types", "top_facets", "caveat", "best_source_grade",
];

export function detail(row: Row): string {
  if (row.src_label || row.dst_label) return edgeDetail(row);
  if (text(row.node_id).startsWith("CLUSTER:") || row.subproject_count || row.edge_count) return clusterDetail(row);
  return recordDetail(row);
}

export function renderDetail(root: HTMLElement, row: Row, mode: DetailMode = "preview", search?: DetailSearchContext): void {
  root.replaceChildren();
  const frame = el("article", "visual-inspector-card");
  frame.classList.add(`is-${mode}`);
  const heading = el("div", "visual-inspector-card-heading");
  heading.append(el("span", "visual-inspector-kind", kind(row)), el("h3", "", title(row)));
  if (mode === "pinned") heading.append(el("span", "visual-inspector-pin", "Pinned"));
  const matches = matchedFields(row, search);
  frame.append(heading);
  if (matches.length) frame.append(matchDetails(matches));
  frame.append(facts(primaryFacts(row)));
  const facets = pretty(row.facet_types || row.top_facets);
  if (facets) frame.append(chips(facets));
  const meta = metadata(row);
  if (meta.length) frame.append(metadataDetails(meta));
  root.appendChild(frame);
}

function clusterDetail(row: Row): string {
  return clean([
    short(row.cluster_label || row.label || "Cluster", 160),
    line("Coverage", sentence([count(row.subproject_count, "subproject"), count(row.node_count, "record"), count(row.edge_count, "relationship"), count(row.visible_edge_count, "shown by default")])),
    line("Evidence", sentence([count(row.source_count, "source"), count(row.claim_count, "claim"), count(row.event_count, "event")])),
    line("Dates", dateRange(row.first_date, row.last_date)),
    line("Readiness", pretty(row.readiness)),
    line("Facets", pretty(row.facet_types || row.top_facets)),
  ]).join("\n");
}

function edgeDetail(row: Row): string {
  return clean([
    `${short(row.src_label || row.src_id, 72)} -> ${short(row.dst_label || row.dst_id, 72)}`,
    line("Relationship", sentence([pretty(row.relation_type), pretty(row.relationship_class)])),
    line("Coverage", sentence([count(row.relationship_count, "relationship"), count(row.source_count, "source"), count(row.claim_count, "claim")])),
    line("Evidence", sentence([status(row), row.best_source_grade ? `best grade ${text(row.best_source_grade)}` : "", count(row.independent_source_count, "independent source")])),
    line("Readiness", pretty(row.readiness)),
    line("Facets", pretty(row.facet_types)),
    line("Caveat", short(row.caveat, 220)),
  ]).join("\n");
}

function recordDetail(row: Row): string {
  return clean([
    short(row.label || row.claim_label || row.event_title || row.title || row.source_title || row.record_id || "Record", 180),
    line("Type", pretty(row.layer || row.event_type || row.claim_type || row.record_type)),
    line("Cluster", text(row.cluster_label)),
    line("Evidence", sentence([count(row.source_count, "source"), count(row.claim_count, "claim"), row.best_source_grade ? `best grade ${text(row.best_source_grade)}` : ""])),
    line("Status", status(row)),
    line("Readiness", pretty(row.readiness)),
    line("Facets", pretty(row.facet_types)),
    line("Caveat", short(row.caveat, 220)),
  ]).join("\n");
}

function line(label: string, value: unknown): string {
  const rendered = text(value).trim();
  return rendered ? `${label}: ${rendered}` : "";
}

function count(value: unknown, singular: string): string {
  const n = Number(value || 0);
  return Number.isFinite(n) && n > 0 ? `${n} ${singular}${n === 1 || singular.endsWith("default") ? "" : "s"}` : "";
}

function sentence(values: string[]): string {
  return values.filter(Boolean).join(", ");
}

function pretty(value: unknown): string {
  return text(value).split(";").map((item) => item.replace(/_/g, " ").replace(/\s*:\s*/g, ": ").replace(/\s+/g, " ").trim()).filter(Boolean).join("; ");
}

function status(row: Row): string {
  return sentence([pretty(row.status), row.confidence ? `confidence ${text(row.confidence)}` : ""]);
}

function dateRange(first: unknown, last: unknown): string {
  const start = text(first).trim();
  const end = text(last).trim();
  return start && end && start !== end ? `${start} to ${end}` : start || end;
}

function clean(values: string[]): string[] {
  return values.filter(Boolean);
}

function title(row: Row): string {
  if (row.src_label || row.dst_label) return `${short(row.src_label || row.src_id, 72)} -> ${short(row.dst_label || row.dst_id, 72)}`;
  return short(row.label || row.claim_label || row.event_title || row.title || row.source_title || row.record_id || row.cluster_label || "Record", 180);
}

function kind(row: Row): string {
  if (row.src_label || row.dst_label) return "Relationship";
  if (text(row.node_id).startsWith("CLUSTER:") || row.subproject_count || row.edge_count) return "Cluster";
  return pretty(row.layer || row.event_type || row.claim_type || row.record_type || "Record");
}

function primaryFacts(row: Row): [string, string][] {
  const facts: [string, string][] = [];
  if (row.src_label || row.dst_label) facts.push(["Relationship", sentence([pretty(row.relation_type), pretty(row.relationship_class)])]);
  else facts.push(["Type", kind(row)], ["Cluster", text(row.cluster_label)]);
  facts.push(
    ["Coverage", coverage(row)],
    ["Evidence", sentence([status(row), row.best_source_grade ? `best grade ${text(row.best_source_grade)}` : "", count(row.source_count, "source"), count(row.claim_count, "claim"), count(row.independent_source_count, "independent source")])],
    ["Dates", dateRange(row.first_date || row.start_date, row.last_date || row.end_date)],
    ["Readiness", pretty(row.readiness)],
    ["Caveat", short(row.caveat, 220)],
  );
  return facts.filter(([, value]) => value);
}

function coverage(row: Row): string {
  return sentence([
    count(row.subproject_count, "subproject"),
    count(row.node_count, "record"),
    count(row.edge_count || row.relationship_count, "relationship"),
    count(row.visible_edge_count, "shown by default"),
    count(row.event_count, "event"),
  ]);
}

function facts(rows: [string, string][]): HTMLElement {
  const list = el("dl", "visual-inspector-facts");
  rows.forEach(([label, value]) => {
    list.append(el("dt", "", label), el("dd", "", value));
  });
  return list;
}

function chips(value: string): HTMLElement {
  const wrap = el("div", "visual-inspector-chips");
  value.split(";").map((item) => item.trim()).filter(Boolean).forEach((item) => wrap.append(el("span", "", item)));
  return wrap;
}

function metadata(row: Row): [string, string][] {
  return Object.entries(row)
    .filter(([key, value]) => !PRIMARY_KEYS.has(key) && text(value).trim())
    .map(([key, value]) => [pretty(key), short(value, 240)]);
}

function metadataDetails(rows: [string, string][]): HTMLElement {
  const details = el("details", "visual-inspector-meta");
  details.append(el("summary", "", `Metadata (${rows.length})`), facts(rows));
  return details;
}

function matchedFields(row: Row, search?: DetailSearchContext): [string, string][] {
  const tokens = search?.tokens?.length ? search.tokens : searchTokens(search?.query || "");
  if (!tokens.length) return [];
  const rows: [string, string][] = [];
  for (const key of MATCH_KEYS) {
    const value = text(row[key]).trim();
    if (!value) continue;
    if (tokens.every((token) => normalizeSearch(`${key} ${value}`).includes(token))) {
      rows.push([pretty(key), short(value, 180)]);
    }
  }
  return rows.slice(0, 6);
}

function matchDetails(rows: [string, string][]): HTMLElement {
  const section = el("section", "visual-inspector-matches");
  section.append(el("h4", "", "Matched fields"), facts(rows));
  return section;
}

function searchTokens(query: string): string[] {
  return normalizeSearch(query).split(" ").filter(Boolean);
}

function normalizeSearch(value: string): string {
  return value.toLowerCase()
    .replace(/[_:/|,;()[\]{}-]+/g, " ")
    .replace(/[^a-z0-9.]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className = "", value = ""): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value) node.textContent = value;
  return node;
}
