import type cytoscape from "cytoscape";

import type { Row } from "../../model";
import { text } from "../../model";
import { metricValue } from "../shared";

export const NETWORK_LAYOUT_PADDING = 104;
export const NETWORK_ZOOM_DURATION_MS = 130;
export const NETWORK_ZOOM_MAX_FACTOR = 1.18;
export const NETWORK_ZOOM_MIN_FACTOR = 0.82;
export const NETWORK_ZOOM_STEP = 1.22;
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

export type NetworkSpacing = "compact" | "balanced" | "expanded";

type NetworkLayoutProfile = {
  edgeLength: number;
  repulsion: number;
  overlap: number;
  componentSpacing: number;
  clusterSpacing: number;
  localSpacing: number;
};

export function spacingMode(value: string): NetworkSpacing {
  return value === "compact" || value === "expanded" ? value : "balanced";
}

export function coseLayoutOptions(mode: NetworkSpacing, nodeCount: number, edgeCount: number, clustered: boolean): Record<string, unknown> {
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

export function seedClusterPositions(nodes: cytoscape.NodeCollection, mode: NetworkSpacing, clustered: boolean): void {
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
    const center = { x: xOffset + col * profile.clusterSpacing, y: yOffset + row * profile.clusterSpacing };
    group.sort((left, right) => nodeLayoutRank(right) - nodeLayoutRank(left) || left.id().localeCompare(right.id()));
    group.forEach((node, index) => {
      const angle = index * GOLDEN_ANGLE + groupIndex * 0.47;
      const radius = index === 0 ? 0 : Math.sqrt(index) * profile.localSpacing * (clustered ? 1.1 : 0.96);
      node.position({ x: center.x + Math.cos(angle) * radius, y: center.y + Math.sin(angle) * radius });
    });
  });
}

export function routeParallelEdges(edges: cytoscape.ElementDefinition[]): void {
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
      const data = edge.data ?? {};
      data.parallelCount = count;
      data.parallelIndex = index;
      data.controlDistance = source === target ? 0 : Math.round((index - (count - 1) / 2) * 34);
      data.loopDirection = `${(45 + index * 42) % 360}deg`;
      data.loopSweep = `${Math.min(82, 42 + count * 8)}deg`;
      data.selfLoop = source === target || undefined;
      edge.data = data;
    });
  }
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

function nodeClusterKey(node: cytoscape.NodeSingular): string {
  const row = node.data("row") as Row;
  return text(row.cluster_id || row.cluster_label || row.subproject_id || row.layer || "network");
}

function nodeLayoutRank(node: cytoscape.NodeSingular): number {
  const row = node.data("row") as Row;
  return metricValue(row, "degree") + metricValue(row, "relationship_count", "edge_count") + metricValue(row, "node_count") + metricValue(row, "claim_count");
}
