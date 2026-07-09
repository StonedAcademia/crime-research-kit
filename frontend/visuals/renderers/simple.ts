import * as d3 from "d3";

import type { ConsoleData, Row } from "../model";
import { short, text } from "../model";
import { bindMark, clusterColor, evidenceFootprint, metricValue, svg } from "./shared";

const CLUSTER_METRICS = [
  { key: "record_count", fallback: "node_count", label: "Records", color: "#315b77" },
  { key: "relationship_count", fallback: "edge_count", label: "Relationships", color: "#8061a8" },
  { key: "default_relationship_count", fallback: "visible_edge_count", label: "Visible rels", color: "#3b705c" },
  { key: "claim_count", label: "Claims", color: "#9c5a39" },
  { key: "source_count", label: "Sources", color: "#4f6f8f" },
  { key: "event_count", label: "Events", color: "#65743a" },
];

export function renderBars(root: HTMLElement, data: ConsoleData): void {
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

export function renderClusterOverview(root: HTMLElement, data: ConsoleData): void {
  const rows = [...(data.data.clusters ?? [])].sort(clusterSort);
  const width = 1080;
  const top = 104;
  const rowHeight = 58;
  const height = Math.max(520, top + rows.length * rowHeight + 54);
  const left = 254;
  const metricGap = 14;
  const metricWidth = (width - left - 38 - metricGap * (CLUSTER_METRICS.length - 1)) / CLUSTER_METRICS.length;
  const chart = svg(root, width, height).classed("visual-cluster-overview", true);
  chart.append("text").attr("x", 28).attr("y", 34).attr("class", "visual-title").text("Cluster evidence footprint");
  chart.append("text").attr("x", 28).attr("y", 57).attr("class", "cluster-row-sub").text("Ranked by records, relationships, claims, sources, and events.");
  CLUSTER_METRICS.forEach((metric, idx) => chart.append("text").attr("x", left + idx * (metricWidth + metricGap)).attr("y", 82).attr("class", "cluster-metric-label").text(metric.label));
  if (!rows.length) {
    chart.append("text").attr("x", width / 2).attr("y", height / 2).attr("class", "cluster-row-sub").attr("text-anchor", "middle").text("No cluster data.");
    return;
  }
  const rowGroups = chart.selectAll<SVGGElement, Row>("g.cluster-row").data(rows).join("g").attr("class", "cluster-row").attr("transform", (_, idx) => `translate(0,${top + idx * rowHeight})`);
  rowGroups.append("line").attr("x1", 24).attr("x2", width - 28).attr("y1", -13).attr("y2", -13).attr("class", "cluster-row-rule");
  rowGroups.append("text").attr("x", 28).attr("y", 8).attr("class", "cluster-row-label").text((row) => short(row.cluster_label || row.cluster_id, 32));
  rowGroups.append("text").attr("x", 28).attr("y", 30).attr("class", "cluster-row-sub").text(clusterSubtitle);
  CLUSTER_METRICS.forEach((metric, idx) => addClusterMetric(root, rowGroups, rows, metric, left + idx * (metricWidth + metricGap), metricWidth - 32));
}

function clusterSort(left: Row, right: Row): number {
  const scoreDelta = evidenceFootprint(right) - evidenceFootprint(left);
  if (scoreDelta) return scoreDelta;
  const visibleDelta = metricValue(right, "default_relationship_count", "visible_edge_count") - metricValue(left, "default_relationship_count", "visible_edge_count");
  return visibleDelta || text(left.cluster_label || left.cluster_id).localeCompare(text(right.cluster_label || right.cluster_id));
}

function clusterSubtitle(row: Row): string {
  const facets = text(row.top_facets).replace(/;/g, ", ");
  const score = `${evidenceFootprint(row)} footprint`;
  return facets ? short(`${score} | ${facets}`, 48) : score;
}

function addClusterMetric(root: HTMLElement, rowGroups: d3.Selection<SVGGElement, Row, SVGSVGElement, unknown>, rows: Row[], metric: typeof CLUSTER_METRICS[number], x: number, barWidth: number): void {
  const maxValue = Math.max(1, d3.max(rows, (row) => metricValue(row, metric.key, metric.fallback)) || 1);
  const scale = d3.scaleLinear().domain([0, maxValue]).range([0, barWidth]);
  rowGroups.append("rect").attr("x", x).attr("y", -1).attr("width", barWidth).attr("height", 17).attr("rx", 3).attr("class", "cluster-metric-track");
  bindMark(rowGroups.append("rect").attr("x", x).attr("y", -1).attr("width", (row) => {
    const value = metricValue(row, metric.key, metric.fallback);
    return value > 0 ? Math.max(2, scale(value)) : 0;
  }).attr("height", 17).attr("rx", 3).attr("fill", metric.color), root);
  rowGroups.append("text").attr("x", x + barWidth + 7).attr("y", 12).attr("class", "cluster-metric-value").text((row) => String(metricValue(row, metric.key, metric.fallback)));
}

export function renderTimeline(root: HTMLElement, data: ConsoleData): void {
  const rows = (data.data.events?.length ? data.data.events : data.data.subcases) ?? [];
  const chart = svg(root);
  const lanes = Array.from(new Set(rows.map((row) => text(row.cluster_label || row.subcase_title || row.cluster_id || "timeline"))));
  const years = rows.map((row) => Number((text(row.start_date) || "2000").slice(0, 4))).filter(Number.isFinite);
  const x = d3.scaleLinear().domain(d3.extent(years.length ? years : [2000, 2001]) as [number, number]).nice().range([90, 870]);
  const y = d3.scaleBand().domain(lanes).range([70, 390]).padding(0.35);
  chart.append("text").attr("x", 60).attr("y", 30).attr("class", "visual-title").text("Timeline and movement lanes");
  chart.append("g").attr("transform", "translate(0,390)").call(d3.axisBottom(x).tickFormat(d3.format("d")));
  chart.append("g").attr("transform", "translate(90,0)").call(d3.axisLeft(y));
  bindMark(chart.selectAll("circle").data(rows).join("circle").attr("cx", (row) => x(Number((text(row.start_date) || "2000").slice(0, 4)) || x.domain()[0])).attr("cy", (row) => (y(text(row.cluster_label || row.subcase_title || row.cluster_id || "timeline")) || 0) + y.bandwidth() / 2).attr("r", 7).attr("fill", "#3b705c"), root);
}

export function renderSourceSubproject(root: HTMLElement, data: ConsoleData): void {
  const rows = [...(data.data.edges ?? [])].sort((left, right) => Number(right.record_count || 0) - Number(left.record_count || 0)).slice(0, 90);
  const chart = svg(root, 980, 620);
  const sources = Array.from(new Set(rows.map((row) => text(row.source_title || row.source_id)))).slice(0, 22);
  const projects = Array.from(new Set(rows.map((row) => text(row.subproject_label || row.subproject_id)))).slice(0, 36);
  const left = d3.scaleBand().domain(sources).range([70, 560]).padding(0.18);
  const right = d3.scaleBand().domain(projects).range([70, 560]).padding(0.14);
  chart.append("text").attr("x", 60).attr("y", 34).attr("class", "visual-title").text("Source-to-subproject map");
  chart.append("g").attr("transform", "translate(260,0)").call(d3.axisLeft(left).tickFormat((value) => short(value, 30)));
  chart.append("g").attr("transform", "translate(900,0)").call(d3.axisRight(right).tickFormat((value) => short(value, 26)));
  bindMark(chart.selectAll("line").data(rows.filter((row) => sources.includes(text(row.source_title || row.source_id)) && projects.includes(text(row.subproject_label || row.subproject_id)))).join("line").attr("x1", 270).attr("x2", 890).attr("y1", (row) => (left(text(row.source_title || row.source_id)) || 0) + left.bandwidth() / 2).attr("y2", (row) => (right(text(row.subproject_label || row.subproject_id)) || 0) + right.bandwidth() / 2).attr("stroke", (row) => clusterColor(row.cluster_id)).attr("stroke-width", (row) => Math.max(1, Math.min(7, Number(row.edge_weight || 1) * 2.4))).attr("opacity", 0.58), root);
}
