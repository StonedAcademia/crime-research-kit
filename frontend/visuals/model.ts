export type Row = Record<string, unknown>;
export type ConsoleData = { slug: string; title: string; kind: string; include_private?: boolean; graph_variants?: string[]; data: Record<string, Row[]> };

declare global {
  interface Window {
    __CRK_VISUAL_DATA__?: Record<string, ConsoleData>;
  }
}

const scriptLoads = new Map<string, Promise<void>>();

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

export async function loadConsoleData(root: HTMLElement, variant = "default"): Promise<ConsoleData | null> {
  const slug = root.getAttribute("data-crk-visual-console") || "";
  const key = variant === "default" ? slug : `${slug}:${variant}`;
  if (window.__CRK_VISUAL_DATA__?.[key]) return window.__CRK_VISUAL_DATA__[key];
  const src = dataSrc(root, variant);
  if (src) {
    await loadScript(src);
    return window.__CRK_VISUAL_DATA__?.[key] ?? null;
  }
  const id = root.dataset.visualDataId;
  const script = id ? document.getElementById(id) : null;
  if (!script?.textContent) return null;
  return JSON.parse(script.textContent) as ConsoleData;
}

function dataSrc(root: HTMLElement, variant: string): string {
  const src = root.dataset.visualDataSrc || "";
  if (!src || variant === "default") return src;
  return src.replace(/\.js(?:\?.*)?$/, `.${variant}.js`);
}

function loadScript(src: string): Promise<void> {
  if (scriptLoads.has(src)) return scriptLoads.get(src) as Promise<void>;
  const promise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[data-crk-data-src="${cssEscape(src)}"]`);
    if (existing) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.dataset.crkDataSrc = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Unable to load visual data: ${src}`));
    document.head.appendChild(script);
  });
  scriptLoads.set(src, promise);
  return promise;
}

function cssEscape(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/"/g, "\\\"");
}

export function detail(row: Row): string {
  const label = row.label || row.claim_label || row.event_title || row.title || row.record_id || row.claim_id || row.source_id || row.node_id || "";
  const bits = [
    short(label, 160),
    row.status ? `status: ${text(row.status)}` : "",
    row.readiness ? `readiness: ${text(row.readiness)}` : "",
    row.confidence ? `confidence: ${text(row.confidence)}` : "",
    row.cluster_label ? `cluster: ${text(row.cluster_label)}` : "",
    row.hub_role ? `hub: ${text(row.hub_role)}` : "",
    row.edge_visibility ? `visibility: ${text(row.edge_visibility)}` : "",
    row.edge_weight ? `edge weight: ${text(row.edge_weight)}` : "",
    row.facet_types ? `facets: ${text(row.facet_types)}` : "",
    row.source_count ? `sources: ${text(row.source_count)}` : "",
    row.source_ids ? `source ids: ${short(row.source_ids, 180)}` : "",
    row.caveat ? `caveat: ${short(row.caveat, 180)}` : "",
  ].filter(Boolean);
  return bits.join("\n");
}
