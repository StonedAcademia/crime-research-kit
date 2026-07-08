export type Row = Record<string, unknown>;
export type VisualMode = "public" | "private";
export type ConsoleData = {
  slug: string;
  title: string;
  kind: string;
  include_private?: boolean;
  graph_variants?: string[];
  layout?: string;
  overview_mode?: string;
  show_all_nodes?: boolean;
  data: Record<string, Row[]>;
};

declare global {
  interface Window {
    __CRK_VISUAL_DATA__?: Record<string, ConsoleData>;
  }
}

const scriptLoads = new Map<string, Promise<void>>();
const loadingTimers = new WeakMap<HTMLElement, number>();
const SLOW_LOADING_MS = 10_000;

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

export function showVisualLoading(root: HTMLElement, message = "Loading visual data", note = "Preparing JSON payload..."): void {
  clearLoadingTimer(root);
  root.dataset.visualLoading = "true";
  delete root.dataset.visualState;
  root.setAttribute("aria-busy", "true");
  const indicator = loadingIndicator(root);
  indicator.classList.remove("is-error");
  const title = indicator.querySelector<HTMLElement>("[data-visual-loading-title]");
  const detail = indicator.querySelector<HTMLElement>("[data-visual-loading-detail]");
  const slowNote = indicator.querySelector<HTMLElement>("[data-visual-loading-slow-note]");
  if (title) title.textContent = message;
  if (detail) detail.textContent = note;
  if (slowNote) {
    slowNote.textContent = "Still loading. Large graph data can take a little longer; the page is still working.";
    slowNote.hidden = true;
  }
  loadingTimers.set(root, window.setTimeout(() => {
    const currentNote = root.querySelector<HTMLElement>(":scope > .visual-loading [data-visual-loading-slow-note]");
    if (root.dataset.visualLoading === "true" && currentNote) currentNote.hidden = false;
  }, SLOW_LOADING_MS));
}

export function clearVisualLoading(root: HTMLElement): void {
  clearLoadingTimer(root);
  delete root.dataset.visualLoading;
  root.removeAttribute("aria-busy");
  root.querySelector<HTMLElement>(":scope > .visual-loading")?.remove();
}

export function showVisualError(root: HTMLElement, message: string): void {
  root.replaceChildren();
  showVisualLoading(root, "Unable to load visual data", message);
  clearLoadingTimer(root);
  const indicator = root.querySelector<HTMLElement>(":scope > .visual-loading");
  indicator?.classList.add("is-error");
  root.dataset.visualState = "error";
  delete root.dataset.visualLoading;
  root.removeAttribute("aria-busy");
}

export function waitForVisualPaint(): Promise<void> {
  return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}

export async function loadConsoleData(root: HTMLElement, variant = "default", mode: VisualMode = visualMode(root)): Promise<ConsoleData | null> {
  const slug = root.getAttribute("data-crk-visual-console") || "";
  const baseKey = mode === "private" ? `private:${slug}` : slug;
  const key = variant === "default" ? baseKey : `${baseKey}:${variant}`;
  if (window.__CRK_VISUAL_DATA__?.[key]) return window.__CRK_VISUAL_DATA__[key];
  const src = dataSrc(root, variant, mode);
  if (src) {
    await loadScript(src);
    return window.__CRK_VISUAL_DATA__?.[key] ?? null;
  }
  const id = root.dataset.visualDataId;
  const script = id ? document.getElementById(id) : null;
  if (!script?.textContent) return null;
  return JSON.parse(script.textContent) as ConsoleData;
}

function loadingIndicator(root: HTMLElement): HTMLElement {
  const existing = root.querySelector<HTMLElement>(":scope > .visual-loading");
  if (existing) return existing;
  const indicator = document.createElement("div");
  indicator.className = "visual-loading";
  indicator.setAttribute("role", "status");
  indicator.setAttribute("aria-live", "polite");

  const spinner = document.createElement("span");
  spinner.className = "visual-loading-spinner";
  spinner.setAttribute("aria-hidden", "true");

  const copy = document.createElement("span");
  copy.className = "visual-loading-copy";
  const title = document.createElement("strong");
  title.dataset.visualLoadingTitle = "";
  const detail = document.createElement("small");
  detail.dataset.visualLoadingDetail = "";
  const bar = document.createElement("span");
  bar.className = "visual-loading-bar";
  bar.setAttribute("aria-hidden", "true");
  const barFill = document.createElement("span");
  barFill.className = "visual-loading-bar-fill";
  bar.appendChild(barFill);
  const slowNote = document.createElement("small");
  slowNote.className = "visual-loading-slow-note";
  slowNote.dataset.visualLoadingSlowNote = "";
  slowNote.hidden = true;
  copy.append(title, detail);
  indicator.append(spinner, copy, bar, slowNote);
  root.appendChild(indicator);
  return indicator;
}

function clearLoadingTimer(root: HTMLElement): void {
  const timer = loadingTimers.get(root);
  if (timer !== undefined) {
    window.clearTimeout(timer);
    loadingTimers.delete(root);
  }
}

function visualMode(root: HTMLElement): VisualMode {
  const mode = root.dataset.visualMode || document.body.dataset.crkVisualMode || document.body.dataset.crkDefaultMode || "public";
  return mode === "private" ? "private" : "public";
}

function dataSrc(root: HTMLElement, variant: string, mode: VisualMode): string {
  const src = root.dataset.visualDataSrc || "";
  if (!src) return src;
  const [path, query = ""] = src.split("?", 2);
  const modePath = mode === "private" ? path.replace(/(^|\/)data\//, "$1data/private/") : path;
  const variantPath = variant === "default" ? modePath : modePath.replace(/\.js$/, `.${variant}.js`);
  return query ? `${variantPath}?${query}` : variantPath;
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
