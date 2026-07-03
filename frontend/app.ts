import "htmx.org";

const DEFAULT_INSPECTOR =
  "Hover or click a chart mark to inspect the row, path, source, or status behind it.";
const STOP_WORDS = new Set([
  "with",
  "from",
  "this",
  "that",
  "source",
  "status",
  "claim",
  "event",
  "path",
  "record",
  "count",
  "context",
  "bridge",
]);

function compactDetail(text: string, limit = 360): string {
  if (!text) return "";
  return text.length > limit ? `${text.slice(0, limit - 1)}...` : text;
}

function tokensFor(text: string): Set<string> {
  return new Set(
    (text || "")
      .toLowerCase()
      .split(/[^a-z0-9_:-]+/)
      .filter((token) => token.length > 3 && !STOP_WORDS.has(token))
      .slice(0, 36),
  );
}

function bootReportInteractions(): void {
  const inspector = document.querySelector<HTMLElement>("[data-inspector]");
  const inspectorBody = document.querySelector<HTMLElement>("[data-inspector-body]");
  const search = document.querySelector<HTMLInputElement>("[data-search]");
  const reset = document.querySelector<HTMLButtonElement>("[data-reset]");
  const queryButtons = Array.from(document.querySelectorAll<HTMLButtonElement>("button[data-query]"));
  const tooltip = document.createElement("div");
  const marks = Array.from(document.querySelectorAll<SVGElement>("svg title"))
    .map((title) => title.parentElement as SVGElement | null)
    .filter((mark): mark is SVGElement => Boolean(mark));

  tooltip.className = "chart-tooltip";
  tooltip.setAttribute("role", "status");
  document.body.appendChild(tooltip);

  function detailFor(el: Element): string {
    return el.querySelector("title")?.textContent?.trim() ?? "";
  }

  function activeQueries(): string[] {
    return queryButtons
      .filter((button) => button.getAttribute("aria-pressed") === "true")
      .map((button) => (button.dataset.query ?? "").trim().toLowerCase())
      .filter(Boolean);
  }

  function applyFilterable(queries: string[]): void {
    document.querySelectorAll<HTMLElement>("[data-filterable]").forEach((el) => {
      const hay = (el.dataset.filterable ?? el.textContent ?? "").toLowerCase();
      el.hidden = queries.length > 0 && !queries.some((query) => hay.includes(query));
    });
  }

  function setInspector(text: string, mode = "live"): void {
    if (!inspectorBody) return;
    inspectorBody.textContent = text || DEFAULT_INSPECTOR;
    inspector?.classList.toggle("is-live", Boolean(text) && mode === "live");
    inspector?.classList.toggle("is-selected", Boolean(text) && mode === "selected");
  }

  function eventPoint(event: Event): { x: number; y: number } {
    const target = event.target instanceof Element ? event.target.getBoundingClientRect() : null;
    const pointer = event instanceof MouseEvent ? event : null;
    const x = pointer && Number.isFinite(pointer.clientX) && pointer.clientX ? pointer.clientX : (target?.right ?? 24);
    const y = pointer && Number.isFinite(pointer.clientY) && pointer.clientY ? pointer.clientY : (target?.top ?? 24);
    return { x, y };
  }

  function showTooltip(text: string, event: Event): void {
    if (!text) return;
    const point = eventPoint(event);
    tooltip.textContent = compactDetail(text, 220);
    tooltip.style.left = `${Math.max(8, Math.min(window.innerWidth - 390, point.x + 12))}px`;
    tooltip.style.top = `${Math.max(8, Math.min(window.innerHeight - 140, point.y + 12))}px`;
    tooltip.classList.add("is-visible");
  }

  function hideTooltip(): void {
    tooltip.classList.remove("is-visible");
  }

  function clickFlash(event: Event): void {
    const point = eventPoint(event);
    const flash = document.createElement("span");
    flash.className = "click-flash";
    flash.style.left = `${point.x}px`;
    flash.style.top = `${point.y}px`;
    document.body.appendChild(flash);
    window.setTimeout(() => flash.remove(), 520);
  }

  function selectMark(el: SVGElement, event: Event): void {
    const selectedText = detailFor(el);
    const selectedTokens = tokensFor(selectedText);
    let relatedCount = 0;
    marks.forEach((mark) => {
      mark.classList.remove("is-selected", "is-related", "is-dim");
      if (mark === el) return;
      const otherTokens = tokensFor(detailFor(mark));
      const related = Array.from(selectedTokens).some((token) => otherTokens.has(token));
      if (related) {
        mark.classList.add("is-related");
        relatedCount += 1;
      } else {
        mark.classList.add("is-dim");
      }
    });
    el.classList.add("is-selected");
    setInspector(`${selectedText}${relatedCount ? `\n\nRelated marks highlighted: ${relatedCount}` : ""}`, "selected");
    clickFlash(event);
    showTooltip(selectedText, event);
  }

  function applyQuery(query: string): void {
    const normalized = (query || "").trim().toLowerCase();
    marks.forEach((el) => {
      const visible = !normalized || detailFor(el).toLowerCase().includes(normalized);
      if (!el.classList.contains("is-selected")) {
        el.classList.toggle("is-dim", !visible);
      }
    });
    applyFilterable(normalized ? [normalized] : activeQueries());
  }

  marks.forEach((el) => {
    el.classList.add("interactive-mark");
    el.setAttribute("tabindex", "0");
    el.setAttribute("role", "button");
    el.setAttribute("aria-label", compactDetail(detailFor(el), 120));
    el.addEventListener("mouseenter", (event) => {
      setInspector(detailFor(el), "live");
      showTooltip(detailFor(el), event);
    });
    el.addEventListener("mousemove", (event) => showTooltip(detailFor(el), event));
    el.addEventListener("mouseleave", hideTooltip);
    el.addEventListener("focus", (event) => {
      setInspector(detailFor(el), "live");
      showTooltip(detailFor(el), event);
    });
    el.addEventListener("blur", hideTooltip);
    el.addEventListener("click", (event) => {
      event.stopPropagation();
      selectMark(el, event);
    });
    el.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectMark(el, event);
      }
    });
  });

  search?.addEventListener("input", () => applyQuery(search.value));
  queryButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const wasPressed = button.getAttribute("aria-pressed") === "true";
      const value = button.dataset.query ?? "";
      const query = wasPressed ? "" : value;
      queryButtons.forEach((candidate) => candidate.setAttribute("aria-pressed", "false"));
      if (!wasPressed) button.setAttribute("aria-pressed", "true");
      if (search) search.value = query;
      applyQuery(query);
      setInspector(query ? `Filtered marks containing: ${query}` : "");
    });
  });
  reset?.addEventListener("click", () => {
    if (search) search.value = "";
    hideTooltip();
    marks.forEach((mark) => mark.classList.remove("is-dim", "is-selected", "is-related"));
    queryButtons.forEach((button) => button.setAttribute("aria-pressed", "false"));
    applyFilterable([]);
    setInspector("");
  });
  applyFilterable(activeQueries());
  setInspector("");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootReportInteractions, { once: true });
} else {
  bootReportInteractions();
}
