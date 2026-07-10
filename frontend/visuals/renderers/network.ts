import cytoscape from "cytoscape";

import type { ConsoleData } from "../model";
import { clearVisualLoading, loadConsoleData, showVisualLoading, text, waitForVisualPaint } from "../model";
import { normalizeSearch, rowFacets, searchTokens } from "./shared";
import { createNetworkShell, networkStyle } from "./network/controls";
import { toElements } from "./network/elements";
import {
  addMissingElements,
  applySearchClasses,
  createSelectionController,
  facetNames,
  filterNetwork,
  summaryText,
  type NetworkSearchState,
} from "./network/filters";
import {
  coseLayoutOptions,
  NETWORK_LAYOUT_PADDING,
  NETWORK_ZOOM_DURATION_MS,
  NETWORK_ZOOM_MAX_FACTOR,
  NETWORK_ZOOM_MIN_FACTOR,
  NETWORK_ZOOM_STEP,
  routeParallelEdges,
  seedClusterPositions,
  spacingMode,
} from "./network/layout";
import { bindMobilePinchZoom, networkFitPadding, networkZoomBounds, renderedCanvasCenter } from "./network/viewport";

const VISUAL_SEARCH_EVENT = "crk:visual-search";
const networkBindings = new WeakMap<HTMLElement, AbortController>();

export function renderNetwork(root: HTMLElement, data: ConsoleData): void {
  root.replaceChildren();
  const shell = createNetworkShell(root, data);
  const dataByVariant = new Map<string, ConsoleData>([["default", data]]);
  let searchQuery = root.dataset.visualSearchQuery || "";
  let layoutRun = 0;
  let currentVisible: cytoscape.CollectionReturnValue | undefined;
  const zoomBounds = networkZoomBounds();
  const cy = cytoscape({
    container: shell.canvas,
    boxSelectionEnabled: false,
    minZoom: zoomBounds.minZoom,
    maxZoom: zoomBounds.maxZoom,
    userZoomingEnabled: false,
    wheelSensitivity: 0.08,
    elements: [],
    style: networkStyle,
    layout: { name: "grid", fit: false, padding: NETWORK_LAYOUT_PADDING, avoidOverlap: true, avoidOverlapPadding: 26 },
  });
  const selection = createSelectionController(root, cy, () => searchQuery, () => currentVisible, () => spacingMode(shell.spacing.value));
  cy.on("mouseover", "node,edge", (event) => {
    event.target.addClass("is-hovered");
    if (!selection.pinnedId()) selection.inspect(event.target, "preview");
  });
  cy.on("mouseout", "node,edge", (event) => { event.target.removeClass("is-hovered"); });
  cy.on("tap", "node,edge", (event) => {
    event.stopPropagation();
    selection.pin(event.target);
  });

  const draw = async (runLayout = false) => {
    const variant = shell.scope.value || "default";
    const loadingVariant = !dataByVariant.has(variant);
    if (loadingVariant) {
      showVisualLoading(root, "Loading relationship data", `Preparing ${variant} graph payload...`);
      shell.summary.textContent = `Loading ${variant} graph payload...`;
      await waitForVisualPaint();
    }
    try {
      const variantData = await ensureVariant(variant);
      const raw = toElements(variantData);
      refreshFacetOptions(raw.edges);
      const wantedFacet = shell.facet.value;
      const facetedEdges = raw.edges.filter((edge) => !wantedFacet || rowFacets(edge.data.row).includes(wantedFacet));
      const result = filterNetwork(raw.nodes, facetedEdges, variantData, currentSearchState());
      routeParallelEdges(result.visibleEdges);
      const added = addMissingElements(cy, raw.nodes, raw.edges);
      currentVisible = showVisible(result.visibleIds);
      applySearchClasses(cy, result);
      shell.summary.textContent = summaryText(result, raw.edges.length, searchQuery);
      if (!result.visibleNodes.length) {
        shell.canvas.dataset.empty = "true";
        shell.canvas.dataset.emptyLabel = result.hasSearch ? "No records or relationships match this search." : "No visible graph data.";
        selection.clear(true);
        return;
      }
      delete shell.canvas.dataset.empty;
      delete shell.canvas.dataset.emptyLabel;
      selection.reconcile(result.visibleIds);
      if (runLayout || added) runLayoutFor(variantData, result.visibleNodes.length, result.visibleEdges.length);
      else settleVisible(currentVisible, ++layoutRun);
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
    return { query, tokens: searchTokens(query), includeContext: shell.searchScope.value !== "matches" };
  }

  function showVisible(visibleIds: Set<string>): cytoscape.CollectionReturnValue {
    cy.elements().forEach((element) => element.toggleClass("is-hidden", !visibleIds.has(element.id())));
    cy.elements().hide();
    let visible = cy.collection();
    visibleIds.forEach((id) => { visible = visible.union(cy.getElementById(id)); });
    visible.show();
    return visible;
  }

  function refreshFacetOptions(edges: cytoscape.ElementDefinition[]): void {
    const current = shell.facet.value;
    const names = facetNames(edges);
    shell.facet.replaceChildren(new Option("All facets", ""));
    names.forEach((name) => shell.facet.add(new Option(name.replace(/_/g, " "), name)));
    if (names.includes(current)) shell.facet.value = current;
  }

  function runLayoutFor(variantData: ConsoleData, nodeCount: number, edgeCount: number): void {
    const preset = variantData.layout === "preset" || toElements(variantData).nodes.some((node) => node.position);
    const mode = spacingMode(shell.spacing.value);
    const clustered = variantData.kind === "cytoscape-clustered-network";
    if (!preset && currentVisible) seedClusterPositions(currentVisible.nodes(), mode, clustered);
    const layout = preset ? { name: "preset", fit: false, padding: NETWORK_LAYOUT_PADDING } : coseLayoutOptions(mode, nodeCount, edgeCount, clustered);
    runGraphLayout(layout, currentVisible);
  }

  function runGraphLayout(layoutOptions: Record<string, unknown>, visible?: cytoscape.CollectionReturnValue): void {
    const token = ++layoutRun;
    const layout = cy.layout(layoutOptions);
    layout.one("layoutstop", () => settleVisible(visible, token));
    layout.run();
  }

  function settleVisible(visible: cytoscape.CollectionReturnValue | undefined, token: number): void {
    if (token !== layoutRun || !visible?.length) return;
    selection.nudge();
    fitVisible(visible, NETWORK_ZOOM_DURATION_MS);
  }

  function fitVisible(visible = currentVisible, duration = 180): void {
    if (!visible?.length) return;
    cy.stop();
    cy.animate({ fit: { eles: visible, padding: networkFitPadding(shell.canvas) } }, { duration, easing: "ease-out" });
  }

  function smoothZoom(targetZoom: number, renderedPosition?: cytoscape.Position): void {
    const zoom = Math.max(cy.minZoom(), Math.min(cy.maxZoom(), targetZoom));
    const animation: cytoscape.AnimationOptions = { zoom };
    if (renderedPosition) animation.pan = panForZoom(zoom, renderedPosition);
    cy.stop();
    cy.animate(animation, { duration: NETWORK_ZOOM_DURATION_MS, easing: "ease-out" });
  }

  function panForZoom(targetZoom: number, renderedPosition: cytoscape.Position): cytoscape.Position {
    const zoom = cy.zoom();
    const pan = cy.pan();
    const graphPosition = { x: (renderedPosition.x - pan.x) / zoom, y: (renderedPosition.y - pan.y) / zoom };
    return { x: renderedPosition.x - graphPosition.x * targetZoom, y: renderedPosition.y - graphPosition.y * targetZoom };
  }

  function renderedPoint(event: WheelEvent): cytoscape.Position {
    const rect = shell.canvas.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  networkBindings.get(root)?.abort();
  const binding = new AbortController();
  networkBindings.set(root, binding);
  bindMobilePinchZoom(shell.canvas, cy, binding.signal);
  root.addEventListener(VISUAL_SEARCH_EVENT, (event) => {
    searchQuery = normalizeSearch((event as CustomEvent<{ query?: string }>).detail?.query || "");
    void draw(false);
  }, { signal: binding.signal });
  shell.canvas.addEventListener("wheel", (event) => {
    if (!currentVisible?.length) return;
    event.preventDefault();
    const factor = Math.max(NETWORK_ZOOM_MIN_FACTOR, Math.min(NETWORK_ZOOM_MAX_FACTOR, Math.exp(-event.deltaY * 0.002)));
    smoothZoom(cy.zoom() * factor, renderedPoint(event));
  }, { passive: false });
  shell.zoomOut.addEventListener("click", () => smoothZoom(cy.zoom() / NETWORK_ZOOM_STEP, renderedCanvasCenter(shell.canvas)));
  shell.zoomIn.addEventListener("click", () => smoothZoom(cy.zoom() * NETWORK_ZOOM_STEP, renderedCanvasCenter(shell.canvas)));
  shell.fitGraph.addEventListener("click", () => fitVisible());
  shell.scope.addEventListener("change", () => {
    root.dataset.visualVariant = shell.scope.value;
    void draw(true);
  });
  shell.spacing.addEventListener("change", () => { void draw(true); });
  shell.searchScope.addEventListener("change", () => { void draw(false); });
  shell.detangle.addEventListener("click", () => { void draw(true); });
  shell.facet.addEventListener("change", () => { void draw(false); });
  void draw(true).catch((error) => { shell.canvas.textContent = error instanceof Error ? error.message : "Unable to render graph."; });
}
