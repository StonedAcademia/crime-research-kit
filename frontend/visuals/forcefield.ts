import type cytoscape from "cytoscape";

export type ForcefieldProfile = "compact" | "balanced" | "expanded";

export type ForcefieldOptions = {
  profile?: ForcefieldProfile;
  pinnedId?: string;
};

type ForceNode = {
  node: cytoscape.NodeSingular;
  x: number;
  y: number;
  radius: number;
  locked: boolean;
};

const MAX_RADIUS = { compact: 54, balanced: 68, expanded: 82 };
const MIN_RADIUS = { compact: 28, balanced: 34, expanded: 42 };
const MAX_PUSH = { compact: 18, balanced: 24, expanded: 30 };
const NEIGHBOR_CELLS = [-1, 0, 1];

export function applyRadiusForcefield(nodes: cytoscape.NodeCollection, options: ForcefieldOptions = {}): void {
  const visible = nodes.filter((node) => node.visible() && !node.hasClass("is-hidden")).toArray();
  if (visible.length < 2) return;
  const profile = options.profile ?? "balanced";
  const items = visible.map((node) => forceNode(node, visible.length, profile, options.pinnedId ?? ""));
  const center = centroid(items);
  const cellSize = Math.max(...items.map((item) => item.radius)) * 2.2;
  const iterations = iterationCount(items.length, profile);
  const hasLocked = items.some((item) => item.locked);
  for (let iteration = 0; iteration < iterations; iteration += 1) {
    const grid = bucketize(items, cellSize);
    let moved = 0;
    for (let index = 0; index < items.length; index += 1) {
      const item = items[index];
      const cellX = Math.floor(item.x / cellSize);
      const cellY = Math.floor(item.y / cellSize);
      for (const offsetX of NEIGHBOR_CELLS) {
        for (const offsetY of NEIGHBOR_CELLS) {
            const bucket = grid.get(key(cellX + offsetX, cellY + offsetY));
            if (!bucket) continue;
            for (const otherIndex of bucket) {
              if (otherIndex <= index) continue;
              moved += separate(item, items[otherIndex], index, otherIndex, profile);
            }
          }
        }
      }
    if (!hasLocked) recenter(items, center);
    if (moved < 0.2) break;
  }
  items.forEach((item) => item.node.position({ x: Math.round(item.x * 100) / 100, y: Math.round(item.y * 100) / 100 }));
}

function forceNode(node: cytoscape.NodeSingular, count: number, profile: ForcefieldProfile, pinnedId: string): ForceNode {
  const position = node.position();
  const width = Number(node.width()) || 24;
  const box = node.boundingBox({ includeLabels: true, includeOverlays: false });
  const boxRadius = Math.max(Number(box.w) || width, Number(box.h) || width) / 2;
  const label = String(node.data("label") ?? "");
  const labelPadding = Math.min(18, label.length * 0.38);
  const explicitRadius = Number(node.data("layoutRadius") ?? 0);
  const degree = Math.max(0, Number(node.data("degree") ?? 0));
  const degreePadding = Math.min(16, Math.sqrt(degree) * 1.7);
  const selectedPadding = node.hasClass("is-pinned") ? 12 : node.hasClass("is-related") ? 5 : 0;
  const radius = clamp(
    Math.max(width / 2, boxRadius, explicitRadius) + labelPadding + densityPadding(count, profile) + degreePadding + selectedPadding,
    MIN_RADIUS[profile],
    MAX_RADIUS[profile],
  );
  return {
    node,
    x: Number(position.x) || 0,
    y: Number(position.y) || 0,
    radius,
    locked: Boolean(pinnedId && node.id() === pinnedId) || node.hasClass("is-pinned"),
  };
}

function densityPadding(count: number, profile: ForcefieldProfile): number {
  const base = profile === "compact" ? 4 : profile === "expanded" ? 18 : 10;
  if (count > 240) return Math.max(0, base - 8);
  if (count > 160) return base - 4;
  if (count > 80) return base;
  if (count > 36) return base + 4;
  return base + 8;
}

function iterationCount(count: number, profile: ForcefieldProfile): number {
  const bonus = profile === "expanded" ? 18 : profile === "balanced" ? 10 : 0;
  if (count > 240) return 38 + bonus;
  if (count > 160) return 48 + bonus;
  if (count > 80) return 64 + bonus;
  return 88 + bonus;
}

function bucketize(items: ForceNode[], cellSize: number): Map<string, number[]> {
  const grid = new Map<string, number[]>();
  items.forEach((item, index) => {
    const cellKey = key(Math.floor(item.x / cellSize), Math.floor(item.y / cellSize));
    const bucket = grid.get(cellKey) ?? [];
    bucket.push(index);
    grid.set(cellKey, bucket);
  });
  return grid;
}

function separate(left: ForceNode, right: ForceNode, leftIndex: number, rightIndex: number, profile: ForcefieldProfile): number {
  const minDistance = left.radius + right.radius;
  let dx = right.x - left.x;
  let dy = right.y - left.y;
  let distance = Math.sqrt(dx * dx + dy * dy);
  if (distance < 0.01) {
    const angle = deterministicAngle(leftIndex, rightIndex);
    dx = Math.cos(angle) * 0.01;
    dy = Math.sin(angle) * 0.01;
    distance = 0.01;
  }
  const overlap = minDistance - distance;
  if (overlap <= 0) return 0;
  if (left.locked && right.locked) return 0;
  const push = Math.min(MAX_PUSH[profile], overlap * 0.62);
  const x = (dx / distance) * push;
  const y = (dy / distance) * push;
  if (left.locked) {
    right.x += x;
    right.y += y;
  } else if (right.locked) {
    left.x -= x;
    left.y -= y;
  } else {
    left.x -= x * 0.5;
    left.y -= y * 0.5;
    right.x += x * 0.5;
    right.y += y * 0.5;
  }
  return overlap;
}

function centroid(items: ForceNode[]): { x: number; y: number } {
  const total = items.reduce((sum, item) => ({ x: sum.x + item.x, y: sum.y + item.y }), { x: 0, y: 0 });
  return { x: total.x / items.length, y: total.y / items.length };
}

function recenter(items: ForceNode[], target: { x: number; y: number }): void {
  const current = centroid(items);
  const dx = target.x - current.x;
  const dy = target.y - current.y;
  items.forEach((item) => {
    item.x += dx;
    item.y += dy;
  });
}

function deterministicAngle(left: number, right: number): number {
  return (((left + 1) * 31 + (right + 1) * 17) % 360) * Math.PI / 180;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function key(x: number, y: number): string {
  return `${x}:${y}`;
}
