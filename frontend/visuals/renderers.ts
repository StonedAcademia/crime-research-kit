import cytoscape from "cytoscape";
import * as d3 from "d3";

import { detail, renderDetail, type DetailMode, type DetailSearchContext } from "./detail";
import { applyRadiusForcefield, type ForcefieldProfile } from "./forcefield";
import type { ConsoleData, Row } from "./model";
import { clearVisualLoading, inspector, loadConsoleData, short, shortId, showVisualLoading, text, waitForVisualPaint } from "./model";

const NETWORK_LAYOUT_PADDING = 104;
const NETWORK_ZOOM_DURATION_MS = 130;
const NETWORK_ZOOM_MAX_FACTOR = 1.18;
const NETWORK_ZOOM_MIN_FACTOR = 0.82;
const NETWORK_ZOOM_STEP = 1.22;
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
const VISUAL_SEARCH_EVENT = "crk:visual-search";

const NETWORK_SEARCH_KEYS = [
  "label", "title", "record_id", "node_id", "cluster_id", "cluster_label", "source_title", "src_id", "src_label",
  "dst_id", "dst_label", "relationship_class", "relation_type", "edge_type", "layer", "record_type", "event_title",
  "event_type", "claim_label", "claim_type", "status", "confidence", "readiness", "facet_types", "top_facets",
  "caveat", "best_source_grade", "subproject_id", "subproject_label",
];

type NetworkSpacing = ForcefieldProfile;

type NetworkLayoutProfile = {
  edgeLength: number;
  repulsion: number;
  overlap: number;
  componentSpacing: number;
  clusterSpacing: number;
  localSpacing: number;
};

type NetworkSearchState = {
  query: string;
  tokens: string[];
  includeContext: boolean;
};

type NetworkFilterResult = {
  visibleNodes: cytoscape.ElementDefinition[];
  visibleEdges: cytoscape.ElementDefinition[];
  directNodeIds: Set<string>;
  directEdgeIds: Set<string>;
  visibleIds: Set<string>;
  hasSearch: boolean;
};

const networkBindings = new WeakMap<HTMLElement, AbortController>();

function bindMark<GElement extends Element, PElement extends d3.BaseType, PDatum>(el: d3.Selection<GElement, Row, PElement, PDatum>, root: HTMLElement): void {
  el.classed("visual-mark", true)
    .attr("tabindex", 0)
    .attr("data-search", (row) => rowSearchText(row))
    .on("mouseenter focus click", (_, row) => {
      const body = inspector(root);
      if (body) renderDetail(body, row, "preview", detailSearchContext(root.dataset.visualSearchQuery || ""));
    });
}

function svg(root: HTMLElement, width = 920, height = 470) {
  root.replaceChildren();
  return d3.select(root).append("svg").attr("viewBox", `0 0 ${width} ${height}`).attr("role", "img");
}

const PALETTE = ["#315b77", "#3b705c", "#9c5a39", "#8061a8", "#b9472d", "#65743a", "#8a5b80", "#4f6f8f", "#7a6a3b"];
const CLUSTER_METRICS = [
  { key: "record_count", fallback: "node_count", label: "Records", color: "#315b77" },
  { key: "relationship_count", fallback: "edge_count", label: "Relationships", color: "#8061a8" },
  { key: "default_relationship_count", fallback: "visible_edge_count", label: "Visible rels", color: "#3b705c" },
  { key: "claim_count", label: "Claims", color: "#9c5a39" },
  { key: "source_count", label: "Sources", color: "#4f6f8f" },
  { key: "event_count", label: "Events", color: "#65743a" },
];
const STRONGEST_MATRIX_LIMIT = 24;

function clusterColor(value: unknown): string {
  const raw = text(value || "cluster");
  let hash = 0;
  for (const char of raw) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return PALETTE[hash % PALETTE.length];
}

function rowFacets(row: Row): string[] {
  return text(row.facet_types).split(";").map((item) => item.trim()).filter(Boolean);
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

function rowSearchText(row: Row): string {
  const keyed = NETWORK_SEARCH_KEYS.map((key) => row[key]);
  return normalizeSearch([detail(row), ...keyed, ...Object.values(row)].map((value) => text(value)).join(" "));
}

function elementMatches(element: cytoscape.ElementDefinition, tokens: string[]): boolean {
  const searchText = text(element.data?.searchText);
  return tokens.length > 0 && tokens.every((token) => searchText.includes(token));
}

function detailSearchContext(query: string, tokens = searchTokens(query)): DetailSearchContext | undefined {
  return tokens.length ? { query, tokens } : undefined;
}

function metricValue(row: Row, key: string, fallback?: string): number {
  const raw = Number(row[key] ?? 0);
  if (Number.isFinite(raw) && raw > 0) return raw;
  const backup = fallback ? Number(row[fallback] ?? 0) : 0;
  return Number.isFinite(backup) ? backup : 0;
}

function evidenceFootprint(row: Row): number {
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

function gradeWeight(value: unknown): number {
  const grade = text(value).trim().toUpperCase();
  if (grade === "A") return 5;
  if (grade === "B") return 4;
  if (grade === "C") return 3;
  if (grade === "D") return 2;
  if (grade === "X") return 1;
  return 0.8;
}

function statusWeight(value: unknown): number {
  const status = text(value).toLowerCase();
  if (/(corroborated|verified|confirmed)/.test(status)) return 5;
  if (/(multiple|triangulated|supported)/.test(status)) return 4;
  if (/(single|candidate|review)/.test(status)) return 2.4;
  if (/(contested|contradict|disputed|blocked)/.test(status)) return 1.2;
  return 1.8;
}

function truthy(value: unknown): boolean {
  return /^(true|1|yes)$/i.test(text(value).trim());
}

function matrixKey(row: Row): string {
  return `${text(row.claim_id)}\u0000${text(row.source_id)}`;
}

function sourceGradeColor(value: unknown): string {
  const grade = text(value).trim().toUpperCase();
  if (grade === "A") return "#315b77";
  if (grade === "B") return "#3b705c";
  if (grade === "C") return "#9c5a39";
  if (grade === "D") return "#b9472d";
  if (grade === "X") return "#65743a";
  return "#8aa39b";
}

function countBy(rows: Row[], key: string): Map<string, number> {
  const counts = new Map<string, number>();
  for (const row of rows) {
    const value = text(row[key]);
    if (!value) continue;
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return counts;
}

function modeButton(label: string): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  return button;
}

function renderBars(root: HTMLElement, data: ConsoleData): void {
  const rows = [...(data.data.readiness ?? []), ...(data.data.sources ?? [])];
  const chart = svg(root);
  const x = d3.scaleBand().domain(rows.map((row, idx) => text(row.readiness || row.grade || idx))).range([60, 870]).padding(0.22);
  const y = d3.scaleLinear().domain([0, d3.max(rows, (row) => Number(row.count || row.claim_count || 1)) || 1]).nice().range([390, 50]);
  chart.append("text").attr("x", 60).attr("y", 30).attr("class", "visual-title").text("Readiness and source-grade distribution");
  bindMark(
    chart.selectAll("rect").data(rows).join("rect")
      .attr("x", (row, idx) => x(text(row.readiness || row.grade || idx)) || 0)
      .attr("y", (row) => y(Number(row.count || row.claim_count || 1)))
      .attr("width", x.bandwidth())
      .attr("height", (row) => 390 - y(Number(row.count || row.claim_count || 1)))
      .attr("fill", (row) => text(row.readiness).includes("blocked") ? "#b9472d" : "#315b77"),
    root,
  );
  chart.append("g").attr("transform", "translate(0,390)").call(d3.axisBottom(x)).selectAll("text").attr("transform", "rotate(-25)").style("text-anchor", "end");
  chart.append("g").attr("transform", "translate(60,0)").call(d3.axisLeft(y).ticks(5));
}

function renderClusterOverview(root: HTMLElement, data: ConsoleData): void {
  const rows = [...(data.data.clusters ?? [])].sort((left, right) => {
    const scoreDelta = evidenceFootprint(right) - evidenceFootprint(left);
    if (scoreDelta) return scoreDelta;
    const visibleDelta = metricValue(right, "default_relationship_count", "visible_edge_count") - metricValue(left, "default_relationship_count", "visible_edge_count");
    if (visibleDelta) return visibleDelta;
    return text(left.cluster_label || left.cluster_id).localeCompare(text(right.cluster_label || right.cluster_id));
  });
  const width = 1080;
  const top = 104;
  const rowHeight = 58;
  const height = Math.max(520, top + rows.length * rowHeight + 54);
  const left = 254;
  const metricGap = 14;
  const metricWidth = (width - left - 38 - metricGap * (CLUSTER_METRICS.length - 1)) / CLUSTER_METRICS.length;
  const chart = svg(root, width, height).classed("visual-cluster-overview", true);

  chart.append("text").attr("x", 28).attr("y", 34).attr("class", "visual-title").text("Cluster evidence footprint");
  chart.append("text")
    .attr("x", 28)
    .attr("y", 57)
    .attr("class", "cluster-row-sub")
    .text("Ranked by records, relationships, claims, sources, and events.");

  CLUSTER_METRICS.forEach((metric, idx) => {
    const x = left + idx * (metricWidth + metricGap);
    chart.append("text").attr("x", x).attr("y", 82).attr("class", "cluster-metric-label").text(metric.label);
  });

  if (!rows.length) {
    chart.append("text").attr("x", width / 2).attr("y", height / 2).attr("class", "cluster-row-sub").attr("text-anchor", "middle").text("No cluster data.");
    return;
  }

  const rowGroups = chart.selectAll<SVGGElement, Row>("g.cluster-row")
    .data(rows)
    .join("g")
    .attr("class", "cluster-row")
    .attr("transform", (_, idx) => `translate(0,${top + idx * rowHeight})`);

  rowGroups.append("line").attr("x1", 24).attr("x2", width - 28).attr("y1", -13).attr("y2", -13).attr("class", "cluster-row-rule");
  rowGroups.append("text")
    .attr("x", 28)
    .attr("y", 8)
    .attr("class", "cluster-row-label")
    .text((row) => short(row.cluster_label || row.cluster_id, 32));
  rowGroups.append("text")
    .attr("x", 28)
    .attr("y", 30)
    .attr("class", "cluster-row-sub")
    .text((row) => {
      const facets = text(row.top_facets).replace(/;/g, ", ");
      const score = `${evidenceFootprint(row)} footprint`;
      return facets ? short(`${score} | ${facets}`, 48) : score;
    });

  CLUSTER_METRICS.forEach((metric, idx) => {
    const x = left + idx * (metricWidth + metricGap);
    const maxValue = Math.max(1, d3.max(rows, (row) => metricValue(row, metric.key, metric.fallback)) || 1);
    const barWidth = metricWidth - 32;
    const scale = d3.scaleLinear().domain([0, maxValue]).range([0, barWidth]);

    rowGroups.append("rect")
      .attr("x", x)
      .attr("y", -1)
      .attr("width", barWidth)
      .attr("height", 17)
      .attr("rx", 3)
      .attr("class", "cluster-metric-track");
    bindMark(
      rowGroups.append("rect")
        .attr("x", x)
        .attr("y", -1)
        .attr("width", (row) => {
          const value = metricValue(row, metric.key, metric.fallback);
          return value > 0 ? Math.max(2, scale(value)) : 0;
        })
        .attr("height", 17)
        .attr("rx", 3)
        .attr("fill", metric.color),
      root,
    );
    rowGroups.append("text")
      .attr("x", x + barWidth + 7)
      .attr("y", 12)
      .attr("class", "cluster-metric-value")
      .text((row) => String(metricValue(row, metric.key, metric.fallback)));
  });
}

function renderTimeline(root: HTMLElement, data: ConsoleData): void {
  const rows = (data.data.events?.length ? data.data.events : data.data.subcases) ?? [];
  const chart = svg(root);
  const lanes = Array.from(new Set(rows.map((row) => text(row.cluster_label || row.subcase_title || row.cluster_id || "timeline"))));
  const years = rows.map((row) => Number((text(row.start_date) || "2000").slice(0, 4))).filter(Number.isFinite);
  const x = d3.scaleLinear().domain(d3.extent(years.length ? years : [2000, 2001]) as [number, number]).nice().range([90, 870]);
  const y = d3.scaleBand().domain(lanes).range([70, 390]).padding(0.35);
  chart.append("text").attr("x", 60).attr("y", 30).attr("class", "visual-title").text("Timeline and movement lanes");
  chart.append("g").attr("transform", "translate(0,390)").call(d3.axisBottom(x).tickFormat(d3.format("d")));
  chart.append("g").attr("transform", "translate(90,0)").call(d3.axisLeft(y));
  bindMark(
    chart.selectAll("circle").data(rows).join("circle")
      .attr("cx", (row) => x(Number((text(row.start_date) || "2000").slice(0, 4)) || x.domain()[0]))
      .attr("cy", (row) => (y(text(row.cluster_label || row.subcase_title || row.cluster_id || "timeline")) || 0) + y.bandwidth() / 2)
      .attr("r", 7)
      .attr("fill", "#3b705c"),
    root,
  );
}

function renderSourceSubproject(root: HTMLElement, data: ConsoleData): void {
  const rows = [...(data.data.edges ?? [])]
    .sort((left, right) => Number(right.record_count || 0) - Number(left.record_count || 0))
    .slice(0, 90);
  const chart = svg(root, 980, 620);
  const sources = Array.from(new Set(rows.map((row) => text(row.source_title || row.source_id)))).slice(0, 22);
  const projects = Array.from(new Set(rows.map((row) => text(row.subproject_label || row.subproject_id)))).slice(0, 36);
  const left = d3.scaleBand().domain(sources).range([70, 560]).padding(0.18);
  const right = d3.scaleBand().domain(projects).range([70, 560]).padding(0.14);
  chart.append("text").attr("x", 60).attr("y", 34).attr("class", "visual-title").text("Source-to-subproject map");
  chart.append("g").attr("transform", "translate(260,0)").call(d3.axisLeft(left).tickFormat((value) => short(value, 30)));
  chart.append("g").attr("transform", "translate(900,0)").call(d3.axisRight(right).tickFormat((value) => short(value, 26)));
  bindMark(
    chart.selectAll("line").data(rows.filter((row) => sources.includes(text(row.source_title || row.source_id)) && projects.includes(text(row.subproject_label || row.subproject_id)))).join("line")
      .attr("x1", 270)
      .attr("x2", 890)
      .attr("y1", (row) => (left(text(row.source_title || row.source_id)) || 0) + left.bandwidth() / 2)
      .attr("y2", (row) => (right(text(row.subproject_label || row.subproject_id)) || 0) + right.bandwidth() / 2)
      .attr("stroke", (row) => clusterColor(row.cluster_id))
      .attr("stroke-width", (row) => Math.max(1, Math.min(7, Number(row.edge_weight || 1) * 2.4)))
      .attr("opacity", 0.58),
    root,
  );
}

function renderMatrix(root: HTMLElement, data: ConsoleData): void {
  root.replaceChildren();
  const rawRows = data.data.matrix ?? [];
  const supportRows = Array.from(new Map(rawRows.filter((row) => text(row.claim_id) && text(row.source_id)).map((row) => [matrixKey(row), row])).values());
  const claimInfo = new Map<string, Row>();
  for (const row of data.data.claims ?? []) {
    const id = text(row.claim_id);
    if (id) claimInfo.set(id, row);
  }
  for (const row of supportRows) {
    const id = text(row.claim_id);
    if (id && !claimInfo.has(id)) claimInfo.set(id, row);
  }
  const sourceInfo = new Map<string, Row>();
  for (const row of supportRows) {
    const id = text(row.source_id);
    if (!id) continue;
    const current = sourceInfo.get(id);
    if (!current || gradeWeight(row.source_grade) > gradeWeight(current.source_grade)) sourceInfo.set(id, row);
  }
  const supportCounts = countBy(supportRows, "claim_id");
  const sourceCounts = countBy(supportRows, "source_id");
  const allClaims = Array.from(new Set(supportRows.map((row) => text(row.claim_id)))).filter(Boolean);
  const allSources = Array.from(new Set(supportRows.map((row) => text(row.source_id)))).filter(Boolean);

  const shell = document.createElement("div");
  shell.className = "visual-matrix-shell";
  const controls = document.createElement("div");
  controls.className = "visual-matrix-controls";
  const strongest = modeButton("Strongest");
  const full = modeButton("Full");
  const summary = document.createElement("div");
  summary.className = "visual-matrix-summary";
  const scroll = document.createElement("div");
  scroll.className = "visual-matrix-scroll";
  controls.append(strongest, full);
  shell.append(controls, summary, scroll);
  root.appendChild(shell);

  let mode: "strongest" | "full" = "strongest";
  const draw = () => {
    const selected = matrixSelection(mode);
    strongest.setAttribute("aria-pressed", String(mode === "strongest"));
    full.setAttribute("aria-pressed", String(mode === "full"));
    summary.textContent = `${mode === "strongest" ? "Strongest" : "Full"}: ${selected.rows.length} support links across ${selected.claims.length} claims and ${selected.sources.length} sources.`;
    scroll.replaceChildren();
    drawMatrixSvg(scroll, selected.claims, selected.sources, selected.rows, mode);
  };

  strongest.addEventListener("click", () => {
    mode = "strongest";
    draw();
  });
  full.addEventListener("click", () => {
    mode = "full";
    draw();
  });
  draw();

  function matrixSelection(nextMode: "strongest" | "full"): { claims: string[]; sources: string[]; rows: Row[] } {
    const rankedClaims = allClaims.sort((left, right) => claimScore(right) - claimScore(left) || left.localeCompare(right));
    const rankedSources = allSources.sort((left, right) => sourceScore(right) - sourceScore(left) || left.localeCompare(right));
    const claims = nextMode === "strongest" ? rankedClaims.slice(0, STRONGEST_MATRIX_LIMIT) : rankedClaims;
    const sources = nextMode === "strongest" ? rankedSources.slice(0, STRONGEST_MATRIX_LIMIT) : rankedSources;
    const claimSet = new Set(claims);
    const sourceSet = new Set(sources);
    const rows = supportRows
      .filter((row) => claimSet.has(text(row.claim_id)) && sourceSet.has(text(row.source_id)))
      .sort((left, right) => cellScore(right) - cellScore(left) || text(left.claim_id).localeCompare(text(right.claim_id)) || text(left.source_id).localeCompare(text(right.source_id)));
    return { claims, sources, rows };
  }

  function claimScore(id: string): number {
    const row = claimInfo.get(id) ?? {};
    const sourceCount = Number(row.source_count ?? supportCounts.get(id) ?? 0);
    const independentCount = Number(row.independent_source_count ?? 0);
    const confidence = Number(row.confidence ?? row.claim_confidence ?? 0);
    const statusScore = Number(row.status_score ?? 0);
    return (
      (supportCounts.get(id) ?? 0) * 6
      + sourceCount * 3
      + independentCount * 4
      + (Number.isFinite(confidence) ? confidence * 4 : 0)
      + (Number.isFinite(statusScore) && statusScore > 0 ? statusScore * 5 : statusWeight(row.status || row.claim_status) * 2)
      + gradeWeight(row.best_source_grade)
    );
  }

  function sourceScore(id: string): number {
    const row = sourceInfo.get(id) ?? {};
    return (sourceCounts.get(id) ?? 0) * 6 + gradeWeight(row.source_grade) * 4;
  }

  function cellScore(row: Row): number {
    return claimScore(text(row.claim_id)) + sourceScore(text(row.source_id)) + gradeWeight(row.source_grade) * 2;
  }

  function claimLabel(id: string): string {
    const row = claimInfo.get(id) ?? {};
    return text(row.claim || row.claim_label || id);
  }

  function sourceLabel(id: string): string {
    const row = sourceInfo.get(id) ?? {};
    return text(row.source_title || id);
  }

  function drawMatrixSvg(target: HTMLElement, claims: string[], sources: string[], rows: Row[], nextMode: "strongest" | "full"): void {
    const compact = nextMode === "full";
    const cell = compact ? 18 : 24;
    const left = compact ? 280 : 240;
    const top = compact ? 176 : 156;
    const width = Math.max(920, left + sources.length * cell + 76);
    const height = Math.max(520, top + claims.length * cell + 64);
    const chart = d3.select(target)
      .append("svg")
      .attr("class", "visual-matrix-chart")
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("width", width)
      .attr("height", height)
      .attr("role", "img");
    chart.append("text").attr("x", 24).attr("y", 34).attr("class", "visual-title").text("Claim-source support matrix");
    chart.append("text")
      .attr("x", 24)
      .attr("y", 57)
      .attr("class", "matrix-summary-label")
      .text(compact ? "Full sparse view: actual support links only." : "Strongest view: highest-support claims and sources.");
    if (!rows.length) {
      chart.append("text").attr("x", width / 2).attr("y", height / 2).attr("class", "matrix-summary-label").attr("text-anchor", "middle").text("No claim-source support links.");
      return;
    }

    const sourceX = new Map(sources.map((id, idx) => [id, left + idx * cell]));
    const claimY = new Map(claims.map((id, idx) => [id, top + idx * cell]));
    chart.selectAll("line.matrix-row-guide")
      .data(claims)
      .join("line")
      .attr("class", "matrix-row-guide")
      .attr("x1", left - 6)
      .attr("x2", left + sources.length * cell)
      .attr("y1", (id) => (claimY.get(id) ?? top) + cell / 2)
      .attr("y2", (id) => (claimY.get(id) ?? top) + cell / 2);
    chart.selectAll("text.matrix-source-label")
      .data(sources)
      .join("text")
      .attr("class", "matrix-source-label")
      .attr("x", (id) => (sourceX.get(id) ?? left) + cell / 2)
      .attr("y", top - 12)
      .attr("transform", (id) => `rotate(-55 ${(sourceX.get(id) ?? left) + cell / 2} ${top - 12})`)
      .text((id) => short(sourceLabel(id), compact ? 20 : 24));
    chart.selectAll("text.matrix-claim-label")
      .data(claims)
      .join("text")
      .attr("class", "matrix-claim-label")
      .attr("x", left - 12)
      .attr("y", (id) => (claimY.get(id) ?? top) + cell * 0.68)
      .text((id) => short(claimLabel(id), compact ? 48 : 42));
    bindMark(
      chart.selectAll("rect.matrix-cell")
        .data(rows)
        .join("rect")
        .attr("class", "matrix-cell")
        .attr("x", (row) => sourceX.get(text(row.source_id)) ?? left)
        .attr("y", (row) => claimY.get(text(row.claim_id)) ?? top)
        .attr("width", cell - 3)
        .attr("height", cell - 3)
        .attr("rx", compact ? 2 : 3)
        .attr("fill", (row) => sourceGradeColor(row.source_grade))
        .attr("stroke", (row) => truthy(row.contradiction_flag) ? "#b9472d" : truthy(row.boundary_flag) ? "#9c5a39" : "#ffffff")
        .attr("stroke-width", (row) => truthy(row.contradiction_flag) || truthy(row.boundary_flag) ? 2.4 : 1),
      root,
    );
  }
}

function spacingMode(value: string): NetworkSpacing {
  return value === "compact" || value === "expanded" ? value : "balanced";
}

function networkLayoutProfile(mode: NetworkSpacing, nodeCount: number, edgeCount: number, clustered: boolean): NetworkLayoutProfile {
  const modeFactor = mode === "compact" ? 0.84 : mode === "expanded" ? 1.24 : 1;
  const densityFactor = Math.min(1.58, Math.max(1, Math.sqrt(Math.max(nodeCount, 1) / 72)));
  const edgeFactor = Math.min(1.32, Math.max(1, edgeCount / Math.max(nodeCount, 1) / 2.4));
  const clusterFactor = clustered ? 1.14 : 1;
  return {
    edgeLength: Math.round(150 * modeFactor * densityFactor * clusterFactor + Math.min(90, nodeCount * 0.34)),
    repulsion: Math.round(27000 * modeFactor * modeFactor * densityFactor * edgeFactor * clusterFactor),
    overlap: Math.round(46 * modeFactor * clusterFactor),
    componentSpacing: Math.round(128 * modeFactor * densityFactor * clusterFactor),
    clusterSpacing: Math.round(340 * modeFactor * densityFactor * clusterFactor),
    localSpacing: Math.round(74 * modeFactor * clusterFactor),
  };
}

function coseLayoutOptions(mode: NetworkSpacing, nodeCount: number, edgeCount: number, clustered: boolean): Record<string, unknown> {
  const profile = networkLayoutProfile(mode, nodeCount, edgeCount, clustered);
  return {
    name: "cose",
    animate: false,
    fit: false,
    padding: NETWORK_LAYOUT_PADDING,
    nodeDimensionsIncludeLabels: true,
    randomize: false,
    nodeRepulsion: profile.repulsion,
    nodeOverlap: profile.overlap,
    componentSpacing: profile.componentSpacing,
    idealEdgeLength: profile.edgeLength,
    edgeElasticity: 42,
    nestingFactor: 1.25,
    gravity: clustered ? 0.12 : 0.18,
    numIter: nodeCount > 180 ? 1300 : nodeCount > 90 ? 1120 : 960,
    initialTemp: 260,
    coolingFactor: 0.94,
    minTemp: 1,
  };
}

function seedClusterPositions(nodes: cytoscape.NodeCollection, mode: NetworkSpacing, clustered: boolean): void {
  const visible = nodes.filter((node) => node.visible() && !node.hasClass("is-hidden")).toArray();
  if (visible.length < 2) return;
  const groups = new Map<string, cytoscape.NodeSingular[]>();
  for (const node of visible) {
    const key = nodeClusterKey(node);
    const group = groups.get(key) ?? [];
    group.push(node);
    groups.set(key, group);
  }
  const sortedGroups = [...groups.entries()].sort((left, right) => right[1].length - left[1].length || left[0].localeCompare(right[0]));
  const profile = networkLayoutProfile(mode, visible.length, 0, clustered);
  const cols = Math.max(1, Math.ceil(Math.sqrt(sortedGroups.length)));
  const rows = Math.ceil(sortedGroups.length / cols);
  const xOffset = -((cols - 1) * profile.clusterSpacing) / 2;
  const yOffset = -((rows - 1) * profile.clusterSpacing) / 2;
  sortedGroups.forEach(([, group], groupIndex) => {
    const col = groupIndex % cols;
    const row = Math.floor(groupIndex / cols);
    const center = {
      x: xOffset + col * profile.clusterSpacing,
      y: yOffset + row * profile.clusterSpacing,
    };
    group.sort((left, right) => nodeLayoutRank(right) - nodeLayoutRank(left) || left.id().localeCompare(right.id()));
    group.forEach((node, index) => {
      const angle = index * GOLDEN_ANGLE + groupIndex * 0.47;
      const radius = index === 0 ? 0 : Math.sqrt(index) * profile.localSpacing * (clustered ? 1.1 : 0.96);
      node.position({ x: center.x + Math.cos(angle) * radius, y: center.y + Math.sin(angle) * radius });
    });
  });
}

function nodeClusterKey(node: cytoscape.NodeSingular): string {
  const row = node.data("row") as Row;
  return text(row.cluster_id || row.cluster_label || row.subproject_id || row.layer || "network");
}

function nodeLayoutRank(node: cytoscape.NodeSingular): number {
  const row = node.data("row") as Row;
  return (
    metricValue(row, "degree")
    + metricValue(row, "relationship_count", "edge_count")
    + metricValue(row, "node_count")
    + metricValue(row, "claim_count")
  );
}

function routeParallelEdges(edges: cytoscape.ElementDefinition[]): void {
  const groups = new Map<string, cytoscape.ElementDefinition[]>();
  for (const edge of edges) {
    const source = text(edge.data?.source);
    const target = text(edge.data?.target);
    if (!source || !target) continue;
    const key = source <= target ? `${source}\u0000${target}` : `${target}\u0000${source}`;
    const group = groups.get(key) ?? [];
    group.push(edge);
    groups.set(key, group);
  }
  for (const group of groups.values()) {
    group.sort((left, right) => text(left.data?.id).localeCompare(text(right.data?.id)));
    group.forEach((edge, index) => {
      const count = group.length;
      const source = text(edge.data?.source);
      const target = text(edge.data?.target);
      const centered = index - (count - 1) / 2;
      const isLoop = source === target;
      const data = edge.data ?? {};
      data.parallelCount = count;
      data.parallelIndex = index;
      data.controlDistance = isLoop ? 0 : Math.round(centered * 34);
      data.loopDirection = `${(45 + index * 42) % 360}deg`;
      data.loopSweep = `${Math.min(82, 42 + count * 8)}deg`;
      data.selfLoop = isLoop || undefined;
      edge.data = data;
    });
  }
}

function renderNetwork(root: HTMLElement, data: ConsoleData): void {
  root.replaceChildren();
  const shell = document.createElement("div");
  shell.className = "visual-network-shell";
  const controls = document.createElement("div");
  controls.className = "visual-network-controls";
  const scope = document.createElement("select");
  scope.setAttribute("aria-label", "Edge visibility");
  (data.graph_variants ?? ["default", "context", "all"]).forEach((value) => {
    const label = value === "default" ? "Backbone" : value === "context" ? "Context" : "All";
    scope.add(new Option(label, value));
  });
  if (root.dataset.visualVariant && Array.from(scope.options).some((option) => option.value === root.dataset.visualVariant)) {
    scope.value = root.dataset.visualVariant;
  }
  const facet = document.createElement("select");
  facet.setAttribute("aria-label", "Relationship facet");
  facet.add(new Option("All facets", ""));
  const spacing = document.createElement("select");
  spacing.setAttribute("aria-label", "Graph spacing");
  spacing.add(new Option("Balanced spacing", "balanced"));
  spacing.add(new Option("Compact spacing", "compact"));
  spacing.add(new Option("Expanded spacing", "expanded"));
  spacing.value = "balanced";
  const searchScope = document.createElement("select");
  searchScope.setAttribute("aria-label", "Search result scope");
  searchScope.add(new Option("Matches + context", "context"));
  searchScope.add(new Option("Matches only", "matches"));
  const detangle = document.createElement("button");
  detangle.type = "button";
  detangle.className = "visual-network-action";
  detangle.textContent = "De-tangle";
  detangle.title = "Re-run graph layout";
  detangle.setAttribute("aria-label", "Re-run graph layout");
  const zoomControls = document.createElement("div");
  zoomControls.className = "visual-network-zoom";
  const zoomOut = zoomButton("-", "Zoom out");
  const fitGraph = zoomButton("[]", "Fit graph");
  const zoomIn = zoomButton("+", "Zoom in");
  zoomControls.append(zoomOut, fitGraph, zoomIn);
  const summary = document.createElement("div");
  summary.className = "visual-network-summary";
  const canvas = document.createElement("div");
  canvas.className = "visual-network-canvas";
  controls.append(scope, facet, spacing, searchScope, detangle, zoomControls);
  shell.append(controls, summary, canvas);
  root.appendChild(shell);

  const dataByVariant = new Map<string, ConsoleData>([["default", data]]);
  let searchQuery = root.dataset.visualSearchQuery || "";
  let pinnedId = "";
  let layoutRun = 0;
  let currentVisible: cytoscape.CollectionReturnValue | undefined;
  const cy = cytoscape({
    container: canvas,
    boxSelectionEnabled: false,
    minZoom: 0.25,
    maxZoom: 2.4,
    userZoomingEnabled: false,
    wheelSensitivity: 0.08,
    elements: [],
    style: [
      { selector: "node,edge", style: { "transition-property": "width height border-width border-color background-color line-color target-arrow-color opacity text-opacity overlay-opacity", "transition-duration": "140ms", "transition-timing-function": "ease-out" } },
      { selector: "node", style: { label: "data(label)", width: 24, height: 24, "background-color": "data(color)", "border-color": "#1d2935", "border-width": 1.8, color: "#191817", "font-size": 8, "min-zoomed-font-size": 7, "text-wrap": "wrap", "text-max-width": 84, "text-valign": "bottom", "text-halign": "center", "text-margin-y": 5, "text-background-color": "#ffffff", "text-background-opacity": 0.78, "text-background-padding": 2 } },
      { selector: "node[hub]", style: { shape: "diamond", width: 18, height: 18, "background-color": "#fffdf8", "border-color": "#b9472d", "border-width": 2.4 } },
      { selector: "edge", style: { width: "data(weight)", "line-color": "#7b8790", "target-arrow-color": "#7b8790", "target-arrow-shape": "triangle", "curve-style": "unbundled-bezier", "control-point-distances": "data(controlDistance)", "control-point-weights": 0.5, "line-cap": "round", opacity: 0.66 } },
      { selector: "edge[parallelCount > 1]", style: { opacity: 0.78 } },
      { selector: "edge[selfLoop]", style: { "curve-style": "bezier", "loop-direction": "data(loopDirection)", "loop-sweep": "data(loopSweep)" } },
      { selector: "edge[visibility = 'context']", style: { "line-style": "dashed", opacity: 0.36 } },
      { selector: "node.is-search-match", style: { width: 32, height: 32, "border-color": "#315b77", "border-width": 3.4, "overlay-color": "#315b77", "overlay-opacity": 0.14, "z-index": 18 } },
      { selector: "edge.is-search-match", style: { width: "mapData(weight, 1, 7, 3, 7)", "line-color": "#315b77", "target-arrow-color": "#315b77", opacity: 0.96, "z-index": 18 } },
      { selector: ".is-search-context", style: { opacity: 0.38, "text-opacity": 0.42 } },
      { selector: "node.is-hovered", style: { width: 30, height: 30, "border-color": "#315b77", "border-width": 3, "overlay-color": "#315b77", "overlay-opacity": 0.08, "z-index": 12 } },
      { selector: "edge.is-hovered", style: { "line-color": "#315b77", "target-arrow-color": "#315b77", opacity: 1, "z-index": 12 } },
      { selector: "node.is-pinned", style: { width: 36, height: 36, "border-color": "#b9472d", "border-width": 4, "background-blacken": -0.08, "overlay-color": "#b9472d", "overlay-opacity": 0.16, "z-index": 24 } },
      { selector: "edge.is-pinned", style: { width: "mapData(weight, 1, 7, 3.5, 8)", "line-color": "#b9472d", "target-arrow-color": "#b9472d", opacity: 1, "overlay-color": "#b9472d", "overlay-opacity": 0.12, "z-index": 24 } },
      { selector: ".is-pinning", style: { "overlay-color": "#b9472d", "overlay-opacity": 0.28 } },
      { selector: "node.is-related", style: { width: 28, height: 28, "border-color": "#9c5a39", "border-width": 2.8, opacity: 0.94, "z-index": 16 } },
      { selector: "edge.is-related", style: { "line-color": "#9c5a39", "target-arrow-color": "#9c5a39", opacity: 0.9, "z-index": 16 } },
      { selector: ".is-muted", style: { opacity: 0.14, "text-opacity": 0.1 } },
    ],
    layout: { name: "grid", fit: false, padding: NETWORK_LAYOUT_PADDING, avoidOverlap: true, avoidOverlapPadding: 26 },
  });

  cy.on("mouseover", "node,edge", (event) => {
    event.target.addClass("is-hovered");
    if (!pinnedId) inspect(event.target, "preview");
  });
  cy.on("mouseout", "node,edge", (event) => {
    event.target.removeClass("is-hovered");
  });
  cy.on("tap", "node,edge", (event) => {
    event.stopPropagation();
    pinElement(event.target);
  });

  const draw = async (runLayout = false) => {
    const variant = scope.value || "default";
    const loadingVariant = !dataByVariant.has(variant);
    if (loadingVariant) {
      showVisualLoading(root, "Loading relationship data", `Preparing ${variant} graph payload...`);
      summary.textContent = `Loading ${variant} graph payload...`;
      await waitForVisualPaint();
    }
    try {
      const variantData = await ensureVariant(variant);
      const raw = toElements(variantData);
      refreshFacetOptions(raw.edges);
      const wantedFacet = facet.value;
      const facetedEdges = raw.edges.filter((edge) => !wantedFacet || rowFacets(edge.data.row).includes(wantedFacet));
      const result = filterNetwork(raw.nodes, facetedEdges, variantData, currentSearchState());
      const { visibleNodes, visibleEdges, visibleIds } = result;
      routeParallelEdges(visibleEdges);
      const added = addMissingElements(raw.nodes, raw.edges);
      cy.elements().forEach((element) => element.toggleClass("is-hidden", !visibleIds.has(element.id())));
      cy.elements().hide();
      let visible = cy.collection();
      visibleIds.forEach((id) => { visible = visible.union(cy.getElementById(id)); });
      visible.show();
      applySearchClasses(result);
      currentVisible = visible;
      summary.textContent = summaryText(result, raw.edges.length);
      if (!visibleNodes.length) {
        canvas.dataset.empty = "true";
        canvas.dataset.emptyLabel = result.hasSearch ? "No records or relationships match this search." : "No visible graph data.";
        clearPinned(true);
        return;
      }
      delete canvas.dataset.empty;
      delete canvas.dataset.emptyLabel;
      reconcilePinned(visibleIds);
      if (runLayout || added) {
        const preset = variantData.layout === "preset" || raw.nodes.some((node) => node.position);
        const mode = spacingMode(spacing.value);
        const clustered = variantData.kind === "cytoscape-clustered-network";
        if (!preset) seedClusterPositions(visible.nodes(), mode, clustered);
        const layout = preset
          ? { name: "preset", fit: false, padding: NETWORK_LAYOUT_PADDING }
          : coseLayoutOptions(mode, visibleNodes.length, visibleEdges.length, clustered);
        runGraphLayout(layout, visible);
      } else {
        settleVisible(visible, ++layoutRun);
      }
    } finally {
      if (loadingVariant) clearVisualLoading(root);
    }
  };

  async function ensureVariant(variant: string): Promise<ConsoleData> {
    if (dataByVariant.has(variant)) return dataByVariant.get(variant) as ConsoleData;
    const loaded = await loadConsoleData(root, variant);
    if (!loaded) throw new Error(`Unable to load ${variant} graph data.`);
    dataByVariant.set(variant, loaded);
    return loaded;
  }

  function currentSearchState(): NetworkSearchState {
    const query = normalizeSearch(searchQuery);
    return { query, tokens: searchTokens(query), includeContext: searchScope.value !== "matches" };
  }

  function filterNetwork(
    nodes: cytoscape.ElementDefinition[],
    edges: cytoscape.ElementDefinition[],
    variantData: ConsoleData,
    search: NetworkSearchState,
  ): NetworkFilterResult {
    const directNodeIds = new Set<string>();
    const directEdgeIds = new Set<string>();
    const hasSearch = search.tokens.length > 0;
    if (!hasSearch) {
      const connectedIds = new Set(edges.flatMap((edge) => [text(edge.data?.source), text(edge.data?.target)]));
      const visibleNodes = variantData.show_all_nodes ? nodes : nodes.filter((node) => connectedIds.has(text(node.data?.id)));
      const visibleIds = new Set([...visibleNodes.map((node) => text(node.data?.id)), ...edges.map((edge) => text(edge.data?.id))]);
      return { visibleNodes, visibleEdges: edges, directNodeIds, directEdgeIds, visibleIds, hasSearch };
    }

    nodes.forEach((node) => {
      const id = text(node.data?.id);
      if (id && elementMatches(node, search.tokens)) directNodeIds.add(id);
    });
    edges.forEach((edge) => {
      const id = text(edge.data?.id);
      if (id && elementMatches(edge, search.tokens)) directEdgeIds.add(id);
    });

    const seedNodeIds = new Set(directNodeIds);
    edges.forEach((edge) => {
      if (!directEdgeIds.has(text(edge.data?.id))) return;
      seedNodeIds.add(text(edge.data?.source));
      seedNodeIds.add(text(edge.data?.target));
    });

    const visibleEdges = search.includeContext
      ? edges.filter((edge) => (
        directEdgeIds.has(text(edge.data?.id))
        || seedNodeIds.has(text(edge.data?.source))
        || seedNodeIds.has(text(edge.data?.target))
      ))
      : edges.filter((edge) => (
        directEdgeIds.has(text(edge.data?.id))
        || (directNodeIds.has(text(edge.data?.source)) && directNodeIds.has(text(edge.data?.target)))
      ));
    const visibleNodeIds = new Set(seedNodeIds);
    visibleEdges.forEach((edge) => {
      visibleNodeIds.add(text(edge.data?.source));
      visibleNodeIds.add(text(edge.data?.target));
    });
    const visibleNodes = nodes.filter((node) => visibleNodeIds.has(text(node.data?.id)));
    const visibleIds = new Set([...visibleNodes.map((node) => text(node.data?.id)), ...visibleEdges.map((edge) => text(edge.data?.id))]);
    return { visibleNodes, visibleEdges, directNodeIds, directEdgeIds, visibleIds, hasSearch };
  }

  function applySearchClasses(result: NetworkFilterResult): void {
    cy.elements().removeClass("is-search-match is-search-context");
    if (!result.hasSearch) return;
    result.visibleIds.forEach((id) => {
      const element = cy.getElementById(id);
      if (element.empty()) return;
      if (result.directNodeIds.has(id) || result.directEdgeIds.has(id)) element.addClass("is-search-match");
      else element.addClass("is-search-context");
    });
  }

  function summaryText(result: NetworkFilterResult, rawEdgeCount: number): string {
    const hiddenEdges = Math.max(0, rawEdgeCount - result.visibleEdges.length);
    if (!result.hasSearch) {
      return `${result.visibleNodes.length} records, ${result.visibleEdges.length} relationships; ${hiddenEdges} filtered relationships hidden.`;
    }
    if (!result.directNodeIds.size && !result.directEdgeIds.size) {
      return `Search "${searchQuery}": no matching records or relationships.`;
    }
    const contextRecords = Math.max(0, result.visibleNodes.length - result.directNodeIds.size);
    return `Search "${searchQuery}": ${result.directNodeIds.size} matching records, ${result.directEdgeIds.size} matching relationships; ${contextRecords} context records and ${result.visibleEdges.length} relationships shown; ${hiddenEdges} relationships hidden.`;
  }

  function addMissingElements(nodes: cytoscape.ElementDefinition[], edges: cytoscape.ElementDefinition[]): boolean {
    let added = false;
    for (const node of nodes) {
      const existing = cy.getElementById(String(node.data?.id));
      if (existing.empty()) {
        cy.add(node);
        added = true;
      } else {
        existing.data(node.data ?? {});
        if (node.position) existing.position(node.position);
      }
    }
    for (const edge of edges) {
      const existing = cy.getElementById(String(edge.data?.id));
      if (existing.empty()) {
        cy.add(edge);
        added = true;
      } else {
        existing.data(edge.data ?? {});
      }
    }
    return added;
  }

  function refreshFacetOptions(edges: cytoscape.ElementDefinition[]): void {
    const current = facet.value;
    const names = Array.from(new Set(edges.flatMap((edge) => rowFacets(edge.data?.row as Row)))).sort();
    facet.replaceChildren(new Option("All facets", ""));
    names.forEach((name) => facet.add(new Option(name.replace(/_/g, " "), name)));
    if (names.includes(current)) facet.value = current;
  }

  function inspect(element: cytoscape.SingularElementReturnValue, mode: DetailMode): void {
    const body = inspector(root);
    if (!body) return;
    renderDetail(body, element.data("row") ?? {}, mode, detailSearchContext(searchQuery));
    setInspectorState(body, mode);
  }

  function setInspectorState(body: HTMLElement, mode: DetailMode | "idle"): void {
    const panel = body.closest<HTMLElement>("[data-visual-inspector]");
    if (!panel) return;
    panel.classList.toggle("is-preview", mode === "preview");
    panel.classList.toggle("is-pinned", mode === "pinned");
    const state = panel.querySelector<HTMLElement>(".visual-inspector-heading span");
    if (state) state.textContent = mode === "pinned" ? "Pinned selection" : mode === "preview" ? "Hover preview" : "Evidence summary";
  }

  function pinElement(element: cytoscape.SingularElementReturnValue): void {
    if (pinnedId === element.id()) {
      clearPinned(true);
      return;
    }
    pinnedId = element.id();
    applyPinnedClasses(element);
    nudgePinnedSpacing();
    element.addClass("is-pinning");
    window.setTimeout(() => element.removeClass("is-pinning"), 360);
    inspect(element, "pinned");
  }

  function applyPinnedClasses(element: cytoscape.SingularElementReturnValue): void {
    cy.elements().removeClass("is-pinned is-related is-muted is-pinning");
    element.addClass("is-pinned");
    const related = element.isNode() ? element.closedNeighborhood() : element.connectedNodes().union(element);
    related.not(element).addClass("is-related");
    cy.elements().not(related).not(element).addClass("is-muted");
  }

  function reconcilePinned(visibleIds: Set<string>): void {
    if (!pinnedId) return;
    const element = cy.getElementById(pinnedId);
    if (element.empty() || !visibleIds.has(pinnedId)) {
      clearPinned(true);
      return;
    }
    applyPinnedClasses(element);
  }

  function clearPinned(resetInspectorBody = false): void {
    if (!pinnedId && !resetInspectorBody) return;
    pinnedId = "";
    cy.elements().removeClass("is-pinned is-related is-muted is-pinning");
    const body = inspector(root);
    if (!body) return;
    if (resetInspectorBody) resetInspector(body);
    else setInspectorState(body, "idle");
  }

  function resetInspector(body: HTMLElement): void {
    body.replaceChildren();
    const placeholder = document.createElement("p");
    placeholder.textContent = "Select or hover a mark to inspect its evidence state.";
    body.appendChild(placeholder);
    setInspectorState(body, "idle");
  }

  function runGraphLayout(layoutOptions: Record<string, unknown>, visible: cytoscape.CollectionReturnValue): void {
    const token = ++layoutRun;
    const layout = cy.layout(layoutOptions);
    layout.one("layoutstop", () => settleVisible(visible, token));
    layout.run();
  }

  function settleVisible(visible: cytoscape.CollectionReturnValue, token: number): void {
    if (token !== layoutRun) return;
    applyRadiusForcefield(visible.nodes(), { profile: spacingMode(spacing.value), pinnedId });
    fitVisible(visible, NETWORK_ZOOM_DURATION_MS);
  }

  function nudgePinnedSpacing(): void {
    if (!currentVisible?.length) return;
    applyRadiusForcefield(currentVisible.nodes(), { profile: spacingMode(spacing.value), pinnedId });
  }

  function handleWheel(event: WheelEvent): void {
    if (!currentVisible?.length) return;
    event.preventDefault();
    const factor = Math.max(NETWORK_ZOOM_MIN_FACTOR, Math.min(NETWORK_ZOOM_MAX_FACTOR, Math.exp(-event.deltaY * 0.002)));
    smoothZoom(cy.zoom() * factor, renderedPoint(event));
  }

  function smoothZoom(targetZoom: number, renderedPosition?: cytoscape.Position): void {
    const zoom = Math.max(cy.minZoom(), Math.min(cy.maxZoom(), targetZoom));
    const animation: cytoscape.AnimationOptions = { zoom };
    if (renderedPosition) animation.pan = panForZoom(zoom, renderedPosition);
    cy.stop();
    cy.animate(animation, { duration: NETWORK_ZOOM_DURATION_MS, easing: "ease-out" });
  }

  function fitVisible(visible = currentVisible, duration = 180): void {
    if (!visible?.length) return;
    cy.stop();
    cy.animate({ fit: { eles: visible, padding: NETWORK_LAYOUT_PADDING } }, { duration, easing: "ease-out" });
  }

  function panForZoom(targetZoom: number, renderedPosition: cytoscape.Position): cytoscape.Position {
    const zoom = cy.zoom();
    const pan = cy.pan();
    const graphPosition = {
      x: (renderedPosition.x - pan.x) / zoom,
      y: (renderedPosition.y - pan.y) / zoom,
    };
    return {
      x: renderedPosition.x - graphPosition.x * targetZoom,
      y: renderedPosition.y - graphPosition.y * targetZoom,
    };
  }

  function renderedPoint(event: WheelEvent): cytoscape.Position {
    const rect = canvas.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  networkBindings.get(root)?.abort();
  const binding = new AbortController();
  networkBindings.set(root, binding);
  root.addEventListener(VISUAL_SEARCH_EVENT, (event) => {
    searchQuery = normalizeSearch((event as CustomEvent<{ query?: string }>).detail?.query || "");
    void draw(false);
  }, { signal: binding.signal });

  canvas.addEventListener("wheel", handleWheel, { passive: false });
  zoomOut.addEventListener("click", () => smoothZoom(cy.zoom() / NETWORK_ZOOM_STEP));
  zoomIn.addEventListener("click", () => smoothZoom(cy.zoom() * NETWORK_ZOOM_STEP));
  fitGraph.addEventListener("click", () => fitVisible());
  scope.addEventListener("change", () => {
    root.dataset.visualVariant = scope.value;
    void draw(true);
  });
  spacing.addEventListener("change", () => { void draw(true); });
  searchScope.addEventListener("change", () => { void draw(false); });
  detangle.addEventListener("click", () => { void draw(true); });
  facet.addEventListener("change", () => { void draw(false); });
  void draw(true).catch((error) => {
    canvas.textContent = error instanceof Error ? error.message : "Unable to render graph.";
  });
}

function zoomButton(label: string, title: string): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.title = title;
  button.setAttribute("aria-label", title);
  return button;
}

function toElements(data: ConsoleData): { nodes: cytoscape.ElementDefinition[]; edges: cytoscape.ElementDefinition[] } {
  const nodes = (data.data.nodes ?? []).map((row) => {
    const x = Number(row.x);
    const y = Number(row.y);
    const position = Number.isFinite(x) && Number.isFinite(y) ? { x, y } : undefined;
    const degree = Math.max(
      metricValue(row, "degree"),
      metricValue(row, "relationship_count", "edge_count"),
      metricValue(row, "visible_edge_count"),
    );
    return {
      data: {
        id: text(row.node_id),
        label: short(row.label, 28),
        row,
        searchText: rowSearchText(row),
        color: clusterColor(row.cluster_id),
        hub: text(row.hub_role) || undefined,
        degree,
        layoutRadius: Math.min(46, 15 + Math.sqrt(Math.max(0, degree)) * 2.8),
      },
      position,
    };
  }).filter((item) => item.data.id);
  const nodeIds = new Set(nodes.map((item) => item.data.id));
  const edges = (data.data.edges ?? [])
    .map((row, idx) => ({ data: { id: text(row.edge_id || idx), source: text(row.src_id), target: text(row.dst_id), label: text(row.relationship_class || row.edge_type), row, searchText: rowSearchText(row), weight: Math.max(1, Math.min(7, Number(row.edge_weight || row.evidence_weight || 1) * 2.2)), visibility: text(row.edge_visibility || "default"), parallelCount: 1, parallelIndex: 0, controlDistance: 0 } }))
    .filter((item) => nodeIds.has(item.data.source) && nodeIds.has(item.data.target));
  return { nodes, edges };
}

export function renderConsoleRoot(root: HTMLElement, data: ConsoleData): void {
  if (data.kind === "cytoscape-network" || data.kind === "cytoscape-clustered-network") renderNetwork(root, data);
  else if (data.kind === "d3-cluster-overview") renderClusterOverview(root, data);
  else if (data.kind === "d3-source-subproject") renderSourceSubproject(root, data);
  else if (data.kind === "d3-timeline") renderTimeline(root, data);
  else if (data.kind === "d3-matrix") renderMatrix(root, data);
  else renderBars(root, data);
}
