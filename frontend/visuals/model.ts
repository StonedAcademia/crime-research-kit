export type Row = Record<string, unknown>;
export type ConsoleData = { slug: string; title: string; kind: string; data: Record<string, Row[]> };

export function text(value: unknown): string {
  return Array.isArray(value) ? value.join("; ") : String(value ?? "");
}

export function short(value: unknown, limit = 120): string {
  const raw = text(value).replace(/\s+/g, " ").trim();
  return raw.length > limit ? `${raw.slice(0, limit - 1)}...` : raw;
}

export function shortId(value: unknown, limit = 18): string {
  return short(text(value).replace(/^S_/, "").replace(/^C_/, "C_"), limit);
}

export function inspector(root: HTMLElement): HTMLElement | null {
  return root.closest(".visual-layout")?.querySelector("[data-visual-inspector-body]") ?? document.querySelector("[data-visual-inspector-body]");
}

export function detail(row: Row): string {
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
