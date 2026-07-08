import cytoscape from "cytoscape";
import * as d3 from "d3";

import type { ConsoleData, Row } from "./model";
import { detail, inspector, loadConsoleData, short, shortId, text } from "./model";

function bindMark(el: d3.Selection<Element, Row, Element, unknown>, root: HTMLElement): void {
  el.classed("visual-mark", true)
    .attr("tabindex", 0)
    .attr("data-search", (row) => detail(row).toLowerCase())
    .on("mouseenter focus click", (_, row) => {
      const body = inspector(root);
      if (body) body.textContent = detail(row);
    });
}

function svg(root: HTMLElement, width = 920, height = 470) {
  root.replaceChildren();
  return d3.select(root).append("svg").attr("viewBox", `0 0 ${width} ${height}`).attr("role", "img");
}

const PALETTE = ["#315b77", "#3b705c", "#9c5a39", "#8061a8", "#b9472d", "#65743a", "#8a5b80", "#4f6f8f", "#7a6a3b"];

function clusterColor(value: unknown): string {
  const raw = text(value || "cluster");
  let hash = 0;
  for (const char of raw) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return PALETTE[hash % PALETTE.length];
}

function rowFacets(row: Row): string[] {
  return text(row.facet_types).split(";").map((item) => item.trim()).filter(Boolean);
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
  const rows = (data.data.clusters ?? []).slice(0, 24);
  const chart = svg(root, 980, 560);
  const y = d3.scaleBand().domain(rows.map((row) => text(row.cluster_label || row.cluster_id))).range([70, 500]).padding(0.16);
  const x = d3.scaleLinear().domain([0, d3.max(rows, (row) => Number(row.subproject_count || row.node_count || 1)) || 1]).nice().range([260, 920]);
  chart.append("text").attr("x", 60).attr("y", 34).attr("class", "visual-title").text("Cluster map");
  chart.append("g").attr("transform", "translate(260,0)").call(d3.axisLeft(y).tickFormat((value) => short(value, 34)));
  chart.append("g").attr("transform", "translate(0,500)").call(d3.axisBottom(x).ticks(6));
  bindMark(
    chart.selectAll("rect").data(rows).join("rect")
      .attr("x", 260)
      .attr("y", (row) => y(text(row.cluster_label || row.cluster_id)) || 0)
      .attr("width", (row) => Math.max(4, x(Number(row.subproject_count || row.node_count || 1)) - 260))
      .attr("height", y.bandwidth())
      .attr("fill", (row) => clusterColor(row.cluster_id)),
    root,
  );
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
  const rows = data.data.matrix ?? [];
  const claims = Array.from(new Set(rows.map((row) => text(row.claim_id)))).slice(0, 18);
  const sources = Array.from(new Set(rows.map((row) => text(row.source_id)))).slice(0, 18);
  const chart = svg(root, 920, 540);
  const x = d3.scaleBand().domain(sources).range([140, 880]).padding(0.08);
  const y = d3.scaleBand().domain(claims).range([132, 470]).padding(0.08);
  chart.append("text").attr("x", 60).attr("y", 30).attr("class", "visual-title").text("Claim-source support matrix");
  chart.append("g").attr("class", "matrix-x-axis").attr("transform", "translate(0,118)").call(d3.axisTop(x).tickFormat((value) => shortId(value, 18)));
  chart.selectAll<SVGTextElement, unknown>(".matrix-x-axis text")
    .attr("transform", "rotate(-36)")
    .attr("dx", "0.25em")
    .attr("dy", "-0.45em")
    .style("text-anchor", "start");
  chart.append("g").attr("transform", "translate(140,0)").call(d3.axisLeft(y));
  bindMark(
    chart.selectAll("rect").data(rows.filter((row) => claims.includes(text(row.claim_id)) && sources.includes(text(row.source_id)))).join("rect")
      .attr("x", (row) => x(text(row.source_id)) || 0)
      .attr("y", (row) => y(text(row.claim_id)) || 0)
      .attr("width", x.bandwidth())
      .attr("height", y.bandwidth())
      .attr("fill", (row) => text(row.source_grade) === "A" ? "#315b77" : text(row.contradiction_flag) === "True" ? "#b9472d" : "#8aa39b"),
    root,
  );
}

function renderSubprojectMatrix(root: HTMLElement, data: ConsoleData): void {
  const rows = data.data.matrix ?? [];
  const numbers = rows.map((row) => Number(row.subproject_number)).filter(Number.isFinite);
  const clusters = Array.from(new Set(rows.map((row) => text(row.cluster_label || row.cluster_id)))).sort();
  const maxNumber = Math.max(1, d3.max(numbers) || 1);
  const height = Math.max(520, 120 + clusters.length * 34);
  const chart = svg(root, 1020, height);
  const x = d3.scaleLinear().domain([1, maxNumber]).range([210, 960]);
  const y = d3.scaleBand().domain(clusters).range([80, height - 70]).padding(0.22);
  chart.append("text").attr("x", 60).attr("y", 34).attr("class", "visual-title").text("Subproject matrix");
  chart.append("g").attr("transform", `translate(0,${height - 70})`).call(d3.axisBottom(x).ticks(12).tickFormat(d3.format("d")));
  chart.append("g").attr("transform", "translate(210,0)").call(d3.axisLeft(y).tickFormat((value) => short(value, 34)));
  bindMark(
    chart.selectAll("rect").data(rows).join("rect")
      .attr("x", (row) => x(Number(row.subproject_number)) - 4)
      .attr("y", (row) => (y(text(row.cluster_label || row.cluster_id)) || 0) + 2)
      .attr("width", 8)
      .attr("height", Math.max(10, y.bandwidth() - 4))
      .attr("rx", 2)
      .attr("fill", (row) => clusterColor(row.cluster_id))
      .attr("opacity", (row) => Number(row.source_count || 0) > 0 ? 0.92 : 0.36),
    root,
  );
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
  const facet = document.createElement("select");
  facet.setAttribute("aria-label", "Relationship facet");
  facet.add(new Option("All facets", ""));
  const summary = document.createElement("div");
  summary.className = "visual-network-summary";
  const canvas = document.createElement("div");
  canvas.className = "visual-network-canvas";
  controls.append(scope, facet);
  shell.append(controls, summary, canvas);
  root.appendChild(shell);

  const dataByVariant = new Map<string, ConsoleData>([["default", data]]);
  const cy = cytoscape({
    container: canvas,
    boxSelectionEnabled: false,
    minZoom: 0.25,
    maxZoom: 2.4,
    elements: [],
    style: [
      { selector: "node", style: { label: "data(label)", width: 24, height: 24, "background-color": "data(color)", "border-color": "#1d2935", "border-width": 1.8, color: "#191817", "font-size": 8, "min-zoomed-font-size": 7, "text-wrap": "wrap", "text-max-width": 84, "text-valign": "bottom", "text-halign": "center", "text-margin-y": 5, "text-background-color": "#ffffff", "text-background-opacity": 0.78, "text-background-padding": 2 } },
      { selector: "node[hub]", style: { shape: "diamond", width: 18, height: 18, "background-color": "#fffdf8", "border-color": "#b9472d", "border-width": 2.4 } },
      { selector: "edge", style: { width: "data(weight)", "line-color": "#7b8790", "target-arrow-color": "#7b8790", "target-arrow-shape": "triangle", "curve-style": "bezier", opacity: 0.72 } },
      { selector: "edge[visibility = 'context']", style: { "line-style": "dashed", opacity: 0.36 } },
    ],
    layout: { name: "grid", fit: true, padding: 96 },
  });
  cy.on("tap mouseover", "node,edge", (event) => {
    const body = inspector(root);
    if (body) body.textContent = detail(event.target.data("row") ?? {});
  });

  const draw = async (runLayout = false) => {
    const variant = scope.value || "default";
    const variantData = await ensureVariant(variant);
    const raw = toElements(variantData);
    const added = addMissingElements(raw.nodes, raw.edges);
    refreshFacetOptions(raw.edges);
    const wantedFacet = facet.value;
    const visibleEdges = raw.edges.filter((edge) => !wantedFacet || rowFacets(edge.data.row).includes(wantedFacet));
    const connectedIds = new Set(visibleEdges.flatMap((edge) => [edge.data.source, edge.data.target]));
    const visibleNodes = raw.nodes.filter((node) => connectedIds.has(node.data.id));
    const visibleIds = new Set([...visibleNodes.map((node) => node.data.id), ...visibleEdges.map((edge) => edge.data.id)]);
    cy.elements().forEach((element) => element.toggleClass("is-hidden", !visibleIds.has(element.id())));
    cy.elements().hide();
    let visible = cy.collection();
    visibleIds.forEach((id) => { visible = visible.union(cy.getElementById(id)); });
    visible.show();
    summary.textContent = `${visibleNodes.length} records, ${visibleEdges.length} relationships; ${Math.max(0, raw.edges.length - visibleEdges.length)} filtered relationships hidden.`;
    if (!visibleNodes.length) {
      canvas.dataset.empty = "true";
      return;
    }
    delete canvas.dataset.empty;
    if (runLayout || added) {
      cy.layout({ name: "cose", animate: false, fit: true, padding: 96, nodeRepulsion: 16000, idealEdgeLength: 135, edgeElasticity: 70, numIter: 700 }).run();
    } else {
      cy.fit(visible, 96);
    }
  };

  async function ensureVariant(variant: string): Promise<ConsoleData> {
    if (dataByVariant.has(variant)) return dataByVariant.get(variant) as ConsoleData;
    const loaded = await loadConsoleData(root, variant);
    if (!loaded) throw new Error(`Unable to load ${variant} graph data.`);
    dataByVariant.set(variant, loaded);
    return loaded;
  }

  function addMissingElements(nodes: cytoscape.ElementDefinition[], edges: cytoscape.ElementDefinition[]): boolean {
    let added = false;
    for (const node of nodes) {
      if (cy.getElementById(String(node.data?.id)).empty()) {
        cy.add(node);
        added = true;
      }
    }
    for (const edge of edges) {
      if (cy.getElementById(String(edge.data?.id)).empty()) {
        cy.add(edge);
        added = true;
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

  scope.addEventListener("change", () => { void draw(true); });
  facet.addEventListener("change", () => { void draw(false); });
  void draw(true).catch((error) => {
    canvas.textContent = error instanceof Error ? error.message : "Unable to render graph.";
  });
}

function toElements(data: ConsoleData): { nodes: cytoscape.ElementDefinition[]; edges: cytoscape.ElementDefinition[] } {
  const nodes = (data.data.nodes ?? []).map((row) => ({
    data: {
      id: text(row.node_id),
      label: short(row.label, 28),
      row,
      color: clusterColor(row.cluster_id),
      hub: text(row.hub_role) || undefined,
    },
  })).filter((item) => item.data.id);
  const nodeIds = new Set(nodes.map((item) => item.data.id));
  const edges = (data.data.edges ?? [])
    .map((row, idx) => ({ data: { id: text(row.edge_id || idx), source: text(row.src_id), target: text(row.dst_id), label: text(row.relationship_class || row.edge_type), row, weight: Math.max(1, Math.min(7, Number(row.edge_weight || row.evidence_weight || 1) * 2.2)), visibility: text(row.edge_visibility || "default") } }))
    .filter((item) => nodeIds.has(item.data.source) && nodeIds.has(item.data.target));
  return { nodes, edges };
}

export function renderConsoleRoot(root: HTMLElement, data: ConsoleData): void {
  if (data.kind === "cytoscape-network" || data.kind === "cytoscape-clustered-network") renderNetwork(root, data);
  else if (data.kind === "d3-cluster-overview") renderClusterOverview(root, data);
  else if (data.kind === "d3-source-subproject") renderSourceSubproject(root, data);
  else if (data.kind === "d3-subproject-matrix") renderSubprojectMatrix(root, data);
  else if (data.kind === "d3-timeline") renderTimeline(root, data);
  else if (data.kind === "d3-matrix") renderMatrix(root, data);
  else renderBars(root, data);
}
