import type cytoscape from "cytoscape";

import type { ConsoleData } from "../../model";

export type NetworkShell = {
  scope: HTMLSelectElement;
  facet: HTMLSelectElement;
  spacing: HTMLSelectElement;
  searchScope: HTMLSelectElement;
  detangle: HTMLButtonElement;
  zoomOut: HTMLButtonElement;
  fitGraph: HTMLButtonElement;
  zoomIn: HTMLButtonElement;
  summary: HTMLElement;
  canvas: HTMLElement;
};

export const networkStyle: cytoscape.Stylesheet[] = [
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
];

export function createNetworkShell(root: HTMLElement, data: ConsoleData): NetworkShell {
  const shell = document.createElement("div");
  shell.className = "visual-network-shell";
  const controls = document.createElement("div");
  controls.className = "visual-network-controls";
  const scope = document.createElement("select");
  scope.setAttribute("aria-label", "Edge visibility");
  (data.graph_variants ?? ["default", "context", "all"]).forEach((value) => scope.add(new Option(value === "default" ? "Backbone" : value === "context" ? "Context" : "All", value)));
  if (root.dataset.visualVariant && Array.from(scope.options).some((option) => option.value === root.dataset.visualVariant)) scope.value = root.dataset.visualVariant;
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
  return { scope, facet, spacing, searchScope, detangle, zoomOut, fitGraph, zoomIn, summary, canvas };
}

function zoomButton(label: string, title: string): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.title = title;
  button.setAttribute("aria-label", title);
  return button;
}
