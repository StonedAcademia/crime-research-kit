import type cytoscape from "cytoscape";

import { renderDetail, type DetailMode } from "../../detail";
import type { ConsoleData, Row } from "../../model";
import { inspector, text } from "../../model";
import { applyRadiusForcefield } from "../../forcefield";
import { detailSearchContext, rowFacets } from "../shared";
import type { NetworkSpacing } from "./layout";

export type NetworkSearchState = {
  query: string;
  tokens: string[];
  includeContext: boolean;
};

export type NetworkFilterResult = {
  visibleNodes: cytoscape.ElementDefinition[];
  visibleEdges: cytoscape.ElementDefinition[];
  directNodeIds: Set<string>;
  directEdgeIds: Set<string>;
  visibleIds: Set<string>;
  hasSearch: boolean;
};

export function filterNetwork(nodes: cytoscape.ElementDefinition[], edges: cytoscape.ElementDefinition[], variantData: ConsoleData, search: NetworkSearchState): NetworkFilterResult {
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
    ? edges.filter((edge) => directEdgeIds.has(text(edge.data?.id)) || seedNodeIds.has(text(edge.data?.source)) || seedNodeIds.has(text(edge.data?.target)))
    : edges.filter((edge) => directEdgeIds.has(text(edge.data?.id)) || (directNodeIds.has(text(edge.data?.source)) && directNodeIds.has(text(edge.data?.target))));
  const visibleNodeIds = new Set(seedNodeIds);
  visibleEdges.forEach((edge) => {
    visibleNodeIds.add(text(edge.data?.source));
    visibleNodeIds.add(text(edge.data?.target));
  });
  const visibleNodes = nodes.filter((node) => visibleNodeIds.has(text(node.data?.id)));
  const visibleIds = new Set([...visibleNodes.map((node) => text(node.data?.id)), ...visibleEdges.map((edge) => text(edge.data?.id))]);
  return { visibleNodes, visibleEdges, directNodeIds, directEdgeIds, visibleIds, hasSearch };
}

export function applySearchClasses(cy: cytoscape.Core, result: NetworkFilterResult): void {
  cy.elements().removeClass("is-search-match is-search-context");
  if (!result.hasSearch) return;
  result.visibleIds.forEach((id) => {
    const element = cy.getElementById(id);
    if (element.empty()) return;
    if (result.directNodeIds.has(id) || result.directEdgeIds.has(id)) element.addClass("is-search-match");
    else element.addClass("is-search-context");
  });
}

export function addMissingElements(cy: cytoscape.Core, nodes: cytoscape.ElementDefinition[], edges: cytoscape.ElementDefinition[]): boolean {
  let added = false;
  for (const item of [...nodes, ...edges]) {
    const existing = cy.getElementById(String(item.data?.id));
    if (existing.empty()) {
      cy.add(item);
      added = true;
    } else {
      existing.data(item.data ?? {});
      if (item.position) existing.position(item.position);
    }
  }
  return added;
}

export function facetNames(edges: cytoscape.ElementDefinition[]): string[] {
  return Array.from(new Set(edges.flatMap((edge) => rowFacets(edge.data?.row as Row)))).sort();
}

export function summaryText(result: NetworkFilterResult, rawEdgeCount: number, searchQuery: string): string {
  const hiddenEdges = Math.max(0, rawEdgeCount - result.visibleEdges.length);
  if (!result.hasSearch) return `${result.visibleNodes.length} records, ${result.visibleEdges.length} relationships; ${hiddenEdges} filtered relationships hidden.`;
  if (!result.directNodeIds.size && !result.directEdgeIds.size) return `Search "${searchQuery}": no matching records or relationships.`;
  const contextRecords = Math.max(0, result.visibleNodes.length - result.directNodeIds.size);
  return `Search "${searchQuery}": ${result.directNodeIds.size} matching records, ${result.directEdgeIds.size} matching relationships; ${contextRecords} context records and ${result.visibleEdges.length} relationships shown; ${hiddenEdges} relationships hidden.`;
}

export function createSelectionController(
  root: HTMLElement,
  cy: cytoscape.Core,
  getSearchQuery: () => string,
  getVisible: () => cytoscape.CollectionReturnValue | undefined,
  getSpacing: () => NetworkSpacing,
) {
  let pinnedId = "";
  const setInspectorState = (body: HTMLElement, mode: DetailMode | "idle") => {
    const panel = body.closest<HTMLElement>("[data-visual-inspector]");
    if (!panel) return;
    panel.classList.toggle("is-preview", mode === "preview");
    panel.classList.toggle("is-pinned", mode === "pinned");
    const state = panel.querySelector<HTMLElement>(".visual-inspector-heading span");
    if (state) state.textContent = mode === "pinned" ? "Pinned selection" : mode === "preview" ? "Hover preview" : "Evidence summary";
  };
  const inspect = (element: cytoscape.SingularElementReturnValue, mode: DetailMode) => {
    const body = inspector(root);
    if (!body) return;
    renderDetail(body, element.data("row") ?? {}, mode, detailSearchContext(getSearchQuery()));
    setInspectorState(body, mode);
  };
  const resetInspector = (body: HTMLElement) => {
    body.replaceChildren();
    const placeholder = document.createElement("p");
    placeholder.textContent = "Select or hover a mark to inspect its evidence state.";
    body.appendChild(placeholder);
    setInspectorState(body, "idle");
  };
  const applyPinnedClasses = (element: cytoscape.SingularElementReturnValue) => {
    cy.elements().removeClass("is-pinned is-related is-muted is-pinning");
    element.addClass("is-pinned");
    const related = element.isNode() ? element.closedNeighborhood() : element.connectedNodes().union(element);
    related.not(element).addClass("is-related");
    cy.elements().not(related).not(element).addClass("is-muted");
  };
  return {
    pinnedId: () => pinnedId,
    inspect,
    clear(resetInspectorBody = false) {
      if (!pinnedId && !resetInspectorBody) return;
      pinnedId = "";
      cy.elements().removeClass("is-pinned is-related is-muted is-pinning");
      const body = inspector(root);
      if (!body) return;
      if (resetInspectorBody) resetInspector(body);
      else setInspectorState(body, "idle");
    },
    pin(element: cytoscape.SingularElementReturnValue) {
      if (pinnedId === element.id()) {
        this.clear(true);
        return;
      }
      pinnedId = element.id();
      applyPinnedClasses(element);
      this.nudge();
      element.addClass("is-pinning");
      window.setTimeout(() => element.removeClass("is-pinning"), 360);
      inspect(element, "pinned");
    },
    reconcile(visibleIds: Set<string>) {
      if (!pinnedId) return;
      const element = cy.getElementById(pinnedId);
      if (element.empty() || !visibleIds.has(pinnedId)) this.clear(true);
      else applyPinnedClasses(element);
    },
    nudge() {
      const visible = getVisible();
      if (visible?.length) applyRadiusForcefield(visible.nodes(), { profile: getSpacing(), pinnedId });
    },
  };
}

function elementMatches(element: cytoscape.ElementDefinition, tokens: string[]): boolean {
  const searchText = text(element.data?.searchText);
  return tokens.length > 0 && tokens.every((token) => searchText.includes(token));
}
