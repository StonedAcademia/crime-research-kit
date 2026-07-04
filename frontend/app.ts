import cytoscape from "cytoscape";
import * as d3 from "d3";
import "htmx.org";

type Row = Record<string, unknown>;
type ConsoleData = { slug: string; title: string; kind: string; data: Record<string, Row[]> };

function text(value: unknown): string {
  return Array.isArray(value) ? value.join("; ") : String(value ?? "");
}

function short(value: unknown, limit = 120): string {
  const raw = text(value).replace(/\s+/g, " ").trim();
  return raw.length > limit ? `${raw.slice(0, limit - 1)}...` : raw;
}

function readConsole(root: HTMLElement): ConsoleData | null {
  const id = root.dataset.visualDataId;
  const script = id ? document.getElementById(id) : null;
  if (!script?.textContent) return null;
  return JSON.parse(script.textContent) as ConsoleData;
}

function inspector(root: HTMLElement): HTMLElement | null {
  return root.closest(".visual-layout")?.querySelector("[data-visual-inspector-body]") ?? document.querySelector("[data-visual-inspector-body]");
}

function detail(row: Row): string {
  const label = row.label || row.claim_label || row.event_title || row.title || row.record_id || row.claim_id || row.source_id || row.node_id || "";
  const bits = [
    short(label, 160),
    row.status ? `status: ${text(row.status)}` : "",
    row.readiness ? `readiness: ${text(row.readiness)}` : "",
    row.confidence ? `confidence: ${text(row.confidence)}` : "",
    row.source_count ? `sources: ${text(row.source_count)}` : "",
    row.source_ids ? `source ids: ${short(row.source_ids, 180)}` : "",
    row.caveat ? `caveat: ${short(row.caveat, 180)}` : "",
  ].filter(Boolean);
  return bits.join("\n");
}

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

function renderMatrix(root: HTMLElement, data: ConsoleData): void {
  const rows = data.data.matrix ?? [];
  const claims = Array.from(new Set(rows.map((row) => text(row.claim_id)))).slice(0, 18);
  const sources = Array.from(new Set(rows.map((row) => text(row.source_id)))).slice(0, 18);
  const chart = svg(root);
  const x = d3.scaleBand().domain(sources).range([140, 880]).padding(0.08);
  const y = d3.scaleBand().domain(claims).range([70, 410]).padding(0.08);
  chart.append("text").attr("x", 60).attr("y", 30).attr("class", "visual-title").text("Claim-source support matrix");
  chart.append("g").attr("transform", "translate(0,70)").call(d3.axisTop(x)).selectAll("text").attr("transform", "rotate(-40)").style("text-anchor", "start");
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

function renderNetwork(root: HTMLElement, data: ConsoleData): void {
  root.replaceChildren();
  const nodes = (data.data.nodes ?? []).map((row) => ({ data: { id: text(row.node_id), label: short(row.label, 34), row } })).filter((item) => item.data.id);
  const nodeIds = new Set(nodes.map((item) => item.data.id));
  const edges = (data.data.edges ?? []).map((row, idx) => ({ data: { id: text(row.edge_id || idx), source: text(row.src_id), target: text(row.dst_id), label: text(row.relationship_class || row.edge_type), row } })).filter((item) => nodeIds.has(item.data.source) && nodeIds.has(item.data.target));
  const cy = cytoscape({
    container: root,
    elements: [...nodes, ...edges],
    style: [
      { selector: "node", style: { label: "data(label)", "background-color": "#fff", "border-color": "#315b77", "border-width": 2, color: "#191817", "font-size": 9 } },
      { selector: "edge", style: { width: 1.5, "line-color": "#7b8790", "target-arrow-color": "#7b8790", "target-arrow-shape": "triangle", "curve-style": "bezier", label: "data(label)", "font-size": 7 } },
    ],
    layout: { name: "cose", animate: false, fit: true, padding: 35 },
  });
  cy.on("tap mouseover", "node,edge", (event) => {
    const body = inspector(root);
    if (body) body.textContent = detail(event.target.data("row") ?? {});
  });
}

function bootVisuals(): void {
  document.querySelectorAll<HTMLElement>("[data-crk-visual-console]").forEach((root) => {
    const data = readConsole(root);
    if (!data) return;
    if (data.kind === "cytoscape-network") renderNetwork(root, data);
    else if (data.kind === "d3-timeline") renderTimeline(root, data);
    else if (data.kind === "d3-matrix") renderMatrix(root, data);
    else renderBars(root, data);
  });
  document.querySelectorAll<HTMLInputElement>("[data-visual-search]").forEach((input) => input.addEventListener("input", () => {
    const query = input.value.toLowerCase();
    document.querySelectorAll<SVGElement>(".visual-mark").forEach((mark) => mark.classList.toggle("is-dim", query.length > 0 && !(mark.dataset.search || "").includes(query)));
  }));
}

function bootDeck(): void {
  const slides = Array.from(document.querySelectorAll<HTMLElement>(".deck-slide"));
  const nav = document.querySelector<HTMLElement>("[data-deck-nav]");
  const count = document.querySelector<HTMLElement>("[data-deck-count]");
  let current = 0;
  const go = (idx: number) => {
    current = Math.max(0, Math.min(slides.length - 1, idx));
    slides.forEach((slide, i) => slide.classList.toggle("active", i === current));
    if (count) count.textContent = `${current + 1} / ${slides.length}`;
  };
  slides.forEach((slide, i) => {
    const button = document.createElement("button");
    button.textContent = `${i + 1}. ${slide.dataset.title ?? "Slide"}`;
    button.addEventListener("click", () => go(i));
    nav?.appendChild(button);
  });
  document.querySelector("[data-deck-prev]")?.addEventListener("click", () => go(current - 1));
  document.querySelector("[data-deck-next]")?.addEventListener("click", () => go(current + 1));
  document.addEventListener("keydown", (event) => {
    if (event.key === "ArrowRight") go(current + 1);
    if (event.key === "ArrowLeft") go(current - 1);
  });
  go(0);
}

document.addEventListener("DOMContentLoaded", () => {
  bootVisuals();
  bootDeck();
});
