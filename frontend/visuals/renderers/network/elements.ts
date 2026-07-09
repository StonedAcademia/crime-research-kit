import type cytoscape from "cytoscape";

import type { ConsoleData } from "../../model";
import { short, text } from "../../model";
import { clusterColor, metricValue, rowSearchText } from "../shared";

export function toElements(data: ConsoleData): { nodes: cytoscape.ElementDefinition[]; edges: cytoscape.ElementDefinition[] } {
  const nodes = (data.data.nodes ?? []).map((row) => {
    const x = Number(row.x);
    const y = Number(row.y);
    const position = Number.isFinite(x) && Number.isFinite(y) ? { x, y } : undefined;
    const degree = Math.max(metricValue(row, "degree"), metricValue(row, "relationship_count", "edge_count"), metricValue(row, "visible_edge_count"));
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
    .map((row, idx) => ({
      data: {
        id: text(row.edge_id || idx),
        source: text(row.src_id),
        target: text(row.dst_id),
        label: text(row.relationship_class || row.edge_type),
        row,
        searchText: rowSearchText(row),
        weight: Math.max(1, Math.min(7, Number(row.edge_weight || row.evidence_weight || 1) * 2.2)),
        visibility: text(row.edge_visibility || "default"),
        parallelCount: 1,
        parallelIndex: 0,
        controlDistance: 0,
      },
    }))
    .filter((item) => nodeIds.has(item.data.source) && nodeIds.has(item.data.target));
  return { nodes, edges };
}
