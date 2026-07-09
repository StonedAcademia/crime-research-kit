import type { ConsoleData } from "./model";
import { renderMatrix } from "./renderers/matrix";
import { renderNetwork } from "./renderers/network";
import { renderBars, renderClusterOverview, renderSourceSubproject, renderTimeline } from "./renderers/simple";

export function renderConsoleRoot(root: HTMLElement, data: ConsoleData): void {
  if (data.kind === "cytoscape-network" || data.kind === "cytoscape-clustered-network") renderNetwork(root, data);
  else if (data.kind === "d3-cluster-overview") renderClusterOverview(root, data);
  else if (data.kind === "d3-source-subproject") renderSourceSubproject(root, data);
  else if (data.kind === "d3-timeline") renderTimeline(root, data);
  else if (data.kind === "d3-matrix") renderMatrix(root, data);
  else renderBars(root, data);
}
